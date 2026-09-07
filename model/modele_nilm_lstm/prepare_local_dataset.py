"""
prepare_local_dataset.py
-------------------------
Transforme un CSV brut de mesures locales (timestamp + aggregate + les 4
appareils mesures individuellement) en un CSV "AI-ready", avec les memes
13 features engineered que celles utilisees a l'entrainement original
(voir CONFIG["extra_features"] dans lstm_causal.py) et le meme FEATURE_NAMES
que le bridge Python (mcp_totale_serial_bridge.py).

CSV D'ENTREE ATTENDU (colonnes minimales) :
    time, aggregate, kettle, fridge, microwave, laptop

    - "time"      : timestamp ISO ou parsable par pandas
    - "aggregate" : puissance agregee mesuree par le capteur principal (W)
    - les 4 autres colonnes : puissance de CHAQUE appareil mesuree
      individuellement au meme instant (par tes compteurs separes) -- ce sont
      les labels (ground truth) pour le fine-tuning.

CSV DE SORTIE : memes colonnes + les 13 features engineered.

Usage:
    python prepare_local_dataset.py --input mes_mesures_brutes.csv \
                                     --output local_AI_ready.csv \
                                     --sample-period-s 5
"""

import argparse
import numpy as np
import pandas as pd

# Doit matcher SAMPLE_PERIOD_S dans le bridge Python
DEFAULT_SAMPLE_PERIOD_S = 5

# TODO: verifier que cette valeur correspond exactement a celle utilisee
# lors de l'entrainement original (voir CONFIG dans lstm_test.py / lstm_causal.py)
NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 6


def engineer_features(df: pd.DataFrame, sample_period_s: int) -> pd.DataFrame:
    """Ajoute les 13 features engineered a partir de la colonne 'aggregate'
    et de l'index temporel 'time'. Reproduit exactement FeatureEngineer.compute()
    du bridge, mais de facon vectorisee (pandas) au lieu de streaming."""

    samples_per_min = round(60 / sample_period_s)
    samples_per_5min = round(300 / sample_period_s)

    df = df.copy()
    idx = df.index  # doit etre un DatetimeIndex

    df["hour"] = idx.hour.astype(float)
    df["minute"] = idx.minute.astype(float)
    df["dayofweek"] = idx.dayofweek.astype(float)
    df["is_weekend"] = (idx.dayofweek >= 5).astype(float)
    df["is_night"] = ((idx.hour >= NIGHT_START_HOUR) | (idx.hour < NIGHT_END_HOUR)).astype(float)

    minute_of_day = idx.hour * 60 + idx.minute
    df["time_sin"] = np.sin(2 * np.pi * minute_of_day / 1440)
    df["time_cos"] = np.cos(2 * np.pi * minute_of_day / 1440)

    agg = df["aggregate"]
    df["agg_diff"] = agg.diff().fillna(0.0)
    df["agg_roll_mean_1min"] = agg.rolling(samples_per_min, min_periods=1).mean()
    df["agg_roll_mean_5min"] = agg.rolling(samples_per_5min, min_periods=1).mean()
    df["agg_roll_std_1min"] = agg.rolling(samples_per_min, min_periods=1).std().fillna(0.0)
    df["agg_lag1"] = agg.shift(1).fillna(agg.iloc[0])
    df["agg_lag5"] = agg.shift(5).fillna(agg.iloc[0])

    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CSV brut (time, aggregate, kettle, fridge, microwave, laptop)")
    parser.add_argument("--output", required=True, help="CSV de sortie AI-ready")
    parser.add_argument("--sample-period-s", type=int, default=DEFAULT_SAMPLE_PERIOD_S)
    args = parser.parse_args()

    print(f"📂 Lecture de {args.input} ...")
    df = pd.read_csv(args.input, parse_dates=["time"])
    df = df.set_index("time").sort_index()

    required = ["aggregate", "kettle", "fridge", "microwave", "laptop"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"❌ Colonnes manquantes dans le CSV d'entree : {missing}")

    n_before = len(df)
    df = df.dropna(subset=required)
    print(f"  {n_before:,} lignes lues, {len(df):,} apres suppression des NaN")

    print("⚙️  Calcul des 13 features engineered ...")
    df = engineer_features(df, args.sample_period_s)

    df.to_csv(args.output)
    print(f"✅ Ecrit -> {args.output} ({len(df):,} lignes, {df.shape[1]} colonnes)")
    print(f"\nColonnes : {list(df.columns)}")


if __name__ == "__main__":
    main()
