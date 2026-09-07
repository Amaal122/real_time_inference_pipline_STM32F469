#!/usr/bin/env python3
"""
mcp_totale_serial_bridge.py -- Collecte HTTP depuis la MP15 source
                                 + envoi UART continu vers le STM32F469-DISCO

Remplace le transport MQTT (mcp_totale_mqtt_bridge.py) par une liaison
série directe via le port COM du ST-Link (Virtual COM Port) :

  [MP15 source] --HTTP GET /data--> [ce script] --UART (13 B/paquet)--> [F469]
                                          |
                                          +--> log local .txt (inchangé)
                                          +--> buffer SQLite si le port serie
                                               est indisponible

Format du paquet envoyé (little-endian, 65 octets) :
    offset 0   u32      magic = 0x52574154 ("RWAT")
    offset 4   u32      seq (numero de sequence croissant)
    offset 8   f32[14]  features (voir FEATURE_NAMES ci-dessous, dans cet ordre)
    offset 64  u8       checksum = somme(octets[0:64]) & 0xFF

Les 14 features sont calculees a partir de la seule puissance active agregee
et de l'heure systeme -- aucune n'utilise tension/courant/frequence separement,
donc ces trois valeurs restent loguees localement (TxtStore) mais ne sont plus
envoyees au F469.

Usage :
    python mcp_totale_serial_bridge.py --host 192.168.31.46 --port 80 \
        --serial-port COM5 --baudrate 115200
    python mcp_totale_serial_bridge.py --host 127.0.0.1 --port 9090
        # mode lecture seule pour tester le mock server
"""

import argparse
import json
import logging
import math
import sqlite3
import struct
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERREUR] Installe requests : pip install requests")
    sys.exit(1)

try:
    import serial
    from serial import SerialException
except ImportError:
    print("[ERREUR] Installe pyserial : pip install pyserial")
    sys.exit(1)

try:
    import paho.mqtt.publish as mqtt_publish
except ImportError:
    mqtt_publish = None # optionnel : seulement requis si --mqtt-broker est fourni

# ── Configuration par defaut ──────────────────────────────────────────────────
DEFAULT_HTTP_PORT   = 80
DEFAULT_INTERVAL    = 5
DEFAULT_OUTPUT      = "./mcp_totale_data"
DEFAULT_TIMEOUT     = 5
DEFAULT_BAUDRATE    = 115200
DEFAULT_BUFFER_DB   = "./mcp_bridge_serial_buffer.db"
DEFAULT_LOGFILE     = "./mcp_bridge_serial.log"

NILM_MAGIC_SAMPLE = 0x52574154  # "RWAT" -- meme convention que le pipeline MQTT
PACKET_FORMAT     = "<II14f"     # magic, seq, 14 features (checksum ajoute a part -> 1 octet)
PACKET_SIZE       = struct.calcsize(PACKET_FORMAT) + 1  # 65 octets

# Ordre exact attendu par le modele nilm_v4_w49.keras -- NE PAS REORDONNER
FEATURE_NAMES = [
    "aggregate", "hour", "minute", "dayofweek", "is_weekend", "is_night",
    "time_sin", "time_cos", "agg_diff",
    "agg_roll_mean_1min", "agg_roll_mean_5min", "agg_roll_std_1min",
    "agg_lag1", "agg_lag5",
]

# Cadence d'echantillonnage reelle (doit matcher --interval) -- utilisee pour
# convertir "1 min"/"5 min" en nombre d'echantillons dans l'historique glissant.
SAMPLE_PERIOD_S = 5
SAMPLES_PER_MIN = round(60 / SAMPLE_PERIOD_S)   # 12
SAMPLES_PER_5MIN = round(300 / SAMPLE_PERIOD_S)  # 60

# TODO: confirme ce seuil dans ton script d'entrainement original (config CONFIG)
NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 6

# Facteurs d'echelle firmware (voir bridge MQTT -- meme correction necessaire)


# Bornes physiques plausibles -- rejette les mesures aberrantes avant envoi
FIELD_BOUNDS = {
    "voltage":         (0, 270.0),
    "current":         (0.0, 100.0),
    "frequency":       (45.0, 65.0),
    "power_factor":    (-1.0, 1.0),
    "active_power":    (0.0, 20000.0),
    "reactive_power":  (-20000.0, 20000.0),
    "apparent_power":  (0.0, 20000.0),
}


def setup_logging(logfile: str):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(logfile, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def build_packet(seq: int, features: list[float]) -> bytes:
    """Construit le paquet 65 octets : magic + seq + 14 features + checksum."""
    assert len(features) == 14, f"attendu 14 features, recu {len(features)}"
    body = struct.pack(PACKET_FORMAT, NILM_MAGIC_SAMPLE, seq, *[float(x) for x in features])
    checksum = sum(body) & 0xFF
    return body + bytes([checksum])


class FeatureEngineer:
    """Calcule les 14 features NILM a partir de la puissance agregee + horloge systeme.

    Maintient un historique glissant de puissance (deque) pour les features
    derivees (diff, lag, moyennes/ecart-type glissants). A appeler une fois
    par echantillon recu, dans l'ordre chronologique.
    """

    def __init__(self):
        # 60 = SAMPLES_PER_5MIN, suffisant pour couvrir tous les besoins (lag5, roll_5min)
        self._history = deque(maxlen=SAMPLES_PER_5MIN)

    def compute(self, power_w: float) -> list[float]:
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        dayofweek = now.weekday()  # 0=lundi ... 6=dimanche
        is_weekend = 1.0 if dayofweek >= 5 else 0.0
        is_night = 1.0 if (hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR) else 0.0

        minute_of_day = hour * 60 + minute
        time_sin = math.sin(2 * math.pi * minute_of_day / 1440)
        time_cos = math.cos(2 * math.pi * minute_of_day / 1440)

        # Ajoute l'echantillon courant AVANT de calculer diff/lag/rolling
        self._history.append(power_w)
        hist = list(self._history)  # du plus ancien au plus recent

        agg_diff = power_w - hist[-2] if len(hist) >= 2 else 0.0
        agg_lag1 = hist[-2] if len(hist) >= 2 else power_w
        agg_lag5 = hist[-6] if len(hist) >= 6 else power_w

        win1 = hist[-SAMPLES_PER_MIN:] if len(hist) >= SAMPLES_PER_MIN else hist
        win5 = hist  # deque deja limitee a SAMPLES_PER_5MIN

        agg_roll_mean_1min = sum(win1) / len(win1)
        agg_roll_mean_5min = sum(win5) / len(win5)
        agg_roll_std_1min = (sum((x - agg_roll_mean_1min) ** 2 for x in win1) / len(win1)) ** 0.5

        return [
            power_w, float(hour), float(minute), float(dayofweek), is_weekend,
            is_night, time_sin, time_cos, agg_diff,
            agg_roll_mean_1min, agg_roll_mean_5min, agg_roll_std_1min,
            agg_lag1, agg_lag5,
        ]


# ── Affichage terminal (inchange) ─────────────────────────────────────────────
def display(r: dict):
    ts = r.get("_timestamp", "?")
    print(
        f"[STM32] [{ts}] | "
        f"V:{str(r.get('voltage','?')):>6} V | "
        f"I:{str(r.get('current','?')):>7} A | "
        f"F:{str(r.get('frequency','?')):>7} Hz | "
        f"PF:{str(r.get('power_factor','?')):>6} | "
        f"P:{str(r.get('active_power','?')):>8} W",
        flush=True,
    )


# ── Gestionnaire de fichier texte (rotation mensuelle, inchange) ─────────────
class TxtStore:
    def __init__(self, output_dir: str):
        self.dir = Path(output_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._current_month = datetime.now().strftime("%Y_%m")
        self._file = self._get_file()
        self._count = self._load_count()
        logging.info(f"Fichier actif : {self._file} ({self._count} enreg. existants)")

    def _get_file(self) -> Path:
        return self.dir / f"mcp_totale_{self._current_month}.txt"

    def _load_count(self) -> int:
        if self._file.exists():
            try:
                return sum(1 for _ in self._file.open(encoding="utf-8"))
            except Exception:
                pass
        return 0

    def append(self, r: dict):
        month = datetime.now().strftime("%Y_%m")
        if month != self._current_month:
            self._current_month = month
            self._count = 0
            self._file = self._get_file()
            logging.info(f"Nouveau mois -> {self._file}")

        line = (
            f"[STM32] [{r.get('_timestamp','?')}] | "
            f"V:{str(r.get('voltage','?')):>6} V | "
            f"I:{str(r.get('current','?')):>7} A | "
            f"F:{str(r.get('frequency','?')):>7} Hz | "
            f"PF:{str(r.get('power_factor','?')):>6} | "
            f"P:{str(r.get('active_power','?')):>8} W"
        )
        with open(self._file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        self._count += 1

    def count(self) -> int:
        return self._count


# ── Buffer de secours SQLite (survit aux coupures du port serie) ─────────────
class LocalBuffer:
    """Stocke les vecteurs de features DEJA CALCULES (pas juste power_w) --
    on ne peut pas recalculer agg_diff/lag/rolling apres coup sans fausser
    l'historique, donc on fige les 14 valeurs au moment de la mesure."""

    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS pending (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seq INTEGER NOT NULL,
                features_json TEXT NOT NULL,
                queued_at REAL NOT NULL
            )"""
        )
        self.conn.commit()

    def push(self, seq: int, features: list[float]):
        self.conn.execute(
            "INSERT INTO pending (seq, features_json, queued_at) VALUES (?, ?, ?)",
            (seq, json.dumps(features), time.time()),
        )
        self.conn.commit()

    def flush(self, send_fn) -> int:
        """Tente de reenvoyer tout ce qui est en attente, dans l'ordre. Retourne le nb envoye."""
        rows = self.conn.execute(
            "SELECT id, seq, features_json FROM pending ORDER BY id"
        ).fetchall()
        sent = 0
        for row_id, seq, features_json in rows:
            features = json.loads(features_json)
            if send_fn(seq, features):
                self.conn.execute("DELETE FROM pending WHERE id=?", (row_id,))
                self.conn.commit()
                sent += 1
            else:
                break  # le port est retombe, on retentera au prochain cycle
        return sent

    def pending_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM pending").fetchone()[0]


# ── Collecteur HTTP (inchange) ────────────────────────────────────────────────
class WiFiCollector:
    def __init__(self, host: str, port: int, timeout: int):
        self.url = f"http://{host}:{port}/data"
        self.timeout = timeout
        logging.info(f"Endpoint source : {self.url}")

    def fetch(self) -> dict | None:
        try:
            resp = requests.get(self.url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                logging.warning(f"STM32 source repond : {data['error']}")
                return None

            
            now = datetime.now()
            data["_timestamp"] = now.strftime("%d/%m/%Y %H:%M:%S")
            data["_collected_at"] = now.astimezone(timezone.utc).isoformat()
            return data
        except requests.exceptions.ConnectionError:
            logging.error(f"Impossible de joindre le STM32 source ({self.url})")
            return None
        except requests.exceptions.Timeout:
            logging.error(f"Timeout apres {self.timeout}s")
            return None
        except Exception as e:
            logging.error(f"Erreur de collecte : {e}")
            return None


# ── Validation avant envoi (inchange) ─────────────────────────────────────────
def validate_record(r: dict) -> bool:
    for field, (lo, hi) in FIELD_BOUNDS.items():
        if field not in r:
            continue
        try:
            val = float(r[field])
        except (TypeError, ValueError):
            logging.warning(f"Champ non numerique rejete : {field}={r[field]}")
            return False
        if not (lo <= val <= hi):
            logging.warning(f"Valeur hors bornes rejetee : {field}={val} (attendu [{lo},{hi}])")
            return False
    return True


# ── Publication série (remplace MqttPublisher) ───────────────────────────────
class SerialPublisher:
    def __init__(self, port: str, baudrate: int, reconnect_delay: float = 2.0):
        self.port_name = port
        self.baudrate = baudrate
        self.reconnect_delay = reconnect_delay
        self.ser: serial.Serial | None = None
        self._connect()

    def _connect(self):
        try:
            self.ser = serial.Serial(
                port=self.port_name,
                baudrate=self.baudrate,
                timeout=1,
            )
            logging.info(f"Port serie ouvert : {self.port_name} @ {self.baudrate} bauds")
        except (SerialException, OSError, ValueError) as e:
            logging.error(f"Impossible d'ouvrir le port serie {self.port_name} : {e}")
            self.ser = None

    def send_sample(self, seq: int, features: list[float]) -> bool:
        """Retourne True si l'envoi a reussi, False sinon (le port sera retente au prochain appel)."""
        if self.ser is None or not self.ser.is_open:
            self._connect()
            if self.ser is None:
                return False

        packet = build_packet(seq, features)
        try:
            self.ser.write(packet)
            self.ser.flush()
            return True
        except (SerialException, OSError, ValueError) as e:
            logging.warning(f"Echec d'ecriture serie ({e}) -- port ferme, nouvelle tentative au prochain cycle")
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
            return False

    def close(self):
        if self.ser is not None and self.ser.is_open:
            self.ser.close()
class MqttPublisher:
    """Publie le meme paquet binaire que SerialPublisher, mais via MQTT
    vers l'ESP32, qui le relaie ensuite sur USART6 du STM32."""

    def __init__(self, broker: str, topic: str, mqtt_port: int = 1883):
        if mqtt_publish is None:
            raise RuntimeError("paho-mqtt non installe : pip install paho-mqtt")
        self.broker = broker
        self.topic = topic
        self.mqtt_port = mqtt_port
        logging.info(f"Cible MQTT : {broker}:{mqtt_port} topic='{topic}'")

    def send_sample(self, seq: int, features: list[float]) -> bool:
        packet = build_packet(seq, features)
        try:
            mqtt_publish.single(
                self.topic, payload=packet,
                hostname=self.broker, port=self.mqtt_port,
            )
            return True
        except Exception as e:
            logging.warning(f"Echec de publication MQTT (seq={seq}) : {e}")
            return False

class Normalizer:
    """Applique la meme normalisation que lstm_causal.py (Section 2),
    a partir des constantes exportees dans <scalers>_constants.json."""

    def __init__(self, constants_path: str):
        with open(constants_path, "r", encoding="utf-8") as f:
            c = json.load(f)

        self.agg_mean = c["aggregate"]["mean"]
        self.agg_scale = c["aggregate"]["scale"]

        self.extra_cols = c["extra_features"]["columns"]
        self.extra_min = c["extra_features"]["data_min"]
        self.extra_max = c["extra_features"]["data_max"]

        logging.info(f"Normalizer charge depuis {constants_path} ({len(self.extra_cols)} extra features)")

    def normalize(self, features: list[float]) -> list[float]:
        """features[0] = aggregate (StandardScaler), features[1:] = extras (MinMaxScaler),
        dans le meme ordre que FEATURE_NAMES."""
        assert len(features) == 1 + len(self.extra_cols), \
            f"attendu {1 + len(self.extra_cols)} features, recu {len(features)}"

        out = [ (features[0] - self.agg_mean) / self.agg_scale ]

        for i, raw in enumerate(features[1:]):
            lo, hi = self.extra_min[i], self.extra_max[i]
            span = hi - lo
            norm = (raw - lo) / span if span != 0 else 0.0
            out.append(norm)

        return out

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Bridge HTTP(source MP15) -> UART(cible STM32F469)")
    ap.add_argument("--host", required=True, help="IP de la MP15 source (ex: 192.168.31.46)")
    ap.add_argument("--port", default=DEFAULT_HTTP_PORT, type=int, help="Port HTTP de la source")
    ap.add_argument("--interval", default=DEFAULT_INTERVAL, type=float)
    ap.add_argument("--timeout", default=DEFAULT_TIMEOUT, type=int)
    ap.add_argument("--output", default=DEFAULT_OUTPUT, help="Dossier de log local")
    ap.add_argument("--serial-port", help="Port COM du ST-Link VCP (ex: COM5, /dev/ttyACM0). Optionnel pour test mock uniquement.")
    ap.add_argument("--baudrate", default=DEFAULT_BAUDRATE, type=int)
    ap.add_argument("--buffer-db", default=DEFAULT_BUFFER_DB)
    ap.add_argument("--logfile", default=DEFAULT_LOGFILE)
    ap.add_argument("--scalers-constants", default="nilm_v5_causal_scalers_constants.json",
                 help="exporte par lstm_causal.py -- contient les constantes de normalisation des 14 features")
    ap.add_argument("--mqtt-broker", default="broker.hivemq.com", help="IP du broker MQTT (ex: 192.168.1.XX). Optionnel : active l'envoi parallele vers USART6 via ESP32.")
    ap.add_argument("--mqtt-port", default=1883, type=int)
    ap.add_argument("--mqtt-topic", default="nilm/packet/stm32F4stage")
    ap.add_argument("--no-mqtt", action="store_true",
                 help="Desactive l'envoi MQTT/USART6 meme si --mqtt-broker est defini")
    args = ap.parse_args()

    setup_logging(args.logfile)

    if args.interval != SAMPLE_PERIOD_S:
        logging.warning(
            f"--interval={args.interval}s ne correspond pas a SAMPLE_PERIOD_S={SAMPLE_PERIOD_S}s "
            f"(constante utilisee pour les fenetres glissantes 1min/5min) -- "
            f"modifie SAMPLE_PERIOD_S en haut du script si tu changes la cadence."
        )

    store = TxtStore(args.output)
    collector = WiFiCollector(args.host, args.port, args.timeout)
    buffer = LocalBuffer(args.buffer_db) if args.serial_port else None
    publisher = SerialPublisher(args.serial_port, args.baudrate) if args.serial_port else None
    mqtt_publisher = None if args.no_mqtt else MqttPublisher(args.mqtt_broker, args.mqtt_topic, args.mqtt_port)
    normalizer = Normalizer(args.scalers_constants)
    feature_engineer = FeatureEngineer()

    seq = 0
    logging.info(
        f"Bridge serie demarre -- intervalle {args.interval}s -- "
        f"source http://{args.host}:{args.port} -- "
        + (f"cible {args.serial_port} @ {args.baudrate} bauds" if args.serial_port else "mode test mock sans sortie serie")
    )

    try:
        while True:
            record = collector.fetch()

            if record and validate_record(record):
                store.append(record)
                display(record)

                seq += 1
                power_w = float(record.get("active_power", 0.0))
                # Calcule les 14 features (met a jour l'historique glissant a chaque appel,
                # donc doit etre appele une seule fois par echantillon, dans l'ordre)
                
                raw_features = feature_engineer.compute(power_w)
                normalized_features = normalizer.normalize(raw_features)

                logging.info(
                    f"RAW features      = {[round(x, 4) for x in raw_features]}"
                )
                logging.info(
                    f"NORMALIZED features = {[round(x, 4) for x in normalized_features]}"
                )

                features = normalized_features
                if publisher is not None and buffer is not None:
                    if buffer.pending_count() > 0:
                        flushed = buffer.flush(publisher.send_sample)
                        if flushed:
                            logging.info(f"{flushed} paquet(s) en attente reenvoyes (USART3/PC)")

                    if not publisher.send_sample(seq, features):
                        logging.warning(f"Echec d'envoi USART3 seq={seq}, mise en buffer local")
                        buffer.push(seq, features)

                if mqtt_publisher is not None:
                    if not mqtt_publisher.send_sample(seq, features):
                        logging.warning(f"Echec d'envoi MQTT/USART6 seq={seq} (non bufferise)")
                
            elif record:
                logging.warning("Enregistrement rejete par la validation, ignore")
            else:
                logging.warning("Mesure ignoree (collecte echouee)")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logging.info(
            f"Arret demande -- {store.count()} enregistrements logges, "
            + (f"{buffer.pending_count()} en attente d'envoi" if buffer is not None else "mode test mock sans buffer serie")
        )
        if publisher is not None:
            publisher.close()


if __name__ == "__main__":
    main()
