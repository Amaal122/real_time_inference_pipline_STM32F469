"""
╔══════════════════════════════════════════════════════════════════════════════╗
║     NILM Seq2Point — VERSION 4  (têtes séparées + amplitude corrigée)       ║
║                                                                              ║
║  Corrections v3→v4 :                                                         ║
║  ✅ Tête Dense séparée par appareil (spécialisation)                         ║
║  ✅ Micro-ondes : amplitude corrigée via output scaling                      ║
║  ✅ Laptop : oversample réduit (était trop fort → hallucinations)            ║
║  ✅ Lave-linge : seuil ON relevé à 50W (ignore la veille ~3.5W)             ║
║  ✅ Gradient clipping adaptatif par tête                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import warnings
import json
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks, regularizers
from tensorflow.keras.optimizers import Adam
import gc

warnings.filterwarnings("ignore")
tf.random.set_seed(42)
np.random.seed(42)

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
CONFIG = {
    "data_path": "C:/Users/bougu/Downloads/ukdale_house2_AI_ready.csv",
    "target_appliances": ["kettle", "fridge", "microwave", "laptop"],
    "aggregate_col": "aggregate",
    "extra_features": [
        "hour", "minute", "dayofweek", "is_weekend", "is_night",
        "time_sin", "time_cos",
        "agg_diff", "agg_roll_mean_1min", "agg_roll_mean_5min",
        "agg_roll_std_1min", "agg_lag1", "agg_lag5"
    ],
    "clip_thresholds": {
        "kettle": (0, 2000),
        "fridge":          (0, 400),
        "microwave":       (0, 3000),
        "laptop":          (0, 100),
    },

    # ── Seuils ON corrigés
    "on_thresholds": {
        "kettle": 1200,
        "fridge":           5,
        "microwave":       20,
        "laptop":           2,
    },

    # ── Suréchantillonnage revu
    # laptop réduit 5→2 (évite les hallucinations)
    # microwave augmenté encore (très rare)
    "oversample_ratio": {
        "kettle": 25,
        "fridge":           2,
        "microwave":       20,
        "laptop":           2,
    },

    # ── Poids loss ON/OFF par appareil
    "loss_weights_on":  [10.0, 3.0, 20.0, 3.0],
    "loss_weights_off": [ 1.0, 1.0,  1.0, 1.0],

    "window_size": 49,
    "stride": 10,
    "batch_size": 512,
    "epochs": 80,
    "learning_rate": 5e-4,
    "val_split": 0.15,
    "test_split": 0.10,

    "model_path": "nilm_v5_causal_w49.keras",
    "scalers_path": "nilm_v5_causal_scalers.joblib",
    "output_dir": "nilm_results_v5_causal/",
}

os.makedirs(CONFIG["output_dir"], exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CHARGEMENT & NETTOYAGE
# ══════════════════════════════════════════════════════════════════════════════

def load_and_clean(config):
    print("📂 Chargement des données...")
    df = pd.read_csv(config["data_path"], parse_dates=["time"], index_col="time")

    needed = (
        [config["aggregate_col"]]
        + config["target_appliances"]
        + [c for c in config["extra_features"] if c in df.columns]
    )
    df = df[needed].copy()
    df.dropna(inplace=True)

    df[config["aggregate_col"]] = df[config["aggregate_col"]].clip(lower=0)
    for app, (lo, hi) in config["clip_thresholds"].items():
        if app in df.columns:
            df[app] = df[app].clip(lo, hi)

    df = df[df[config["aggregate_col"]] >= 0]
    print(f"  ✅ {len(df):,} lignes | {df.shape[1]} colonnes")

    print("\n  📊 Statistiques par appareil :")
    for app in config["target_appliances"]:
        thr = config["on_thresholds"][app]
        pct_on   = (df[app] > thr).mean() * 100
        max_val  = df[app].max()
        mean_on  = df[app][df[app] > thr].mean() if pct_on > 0 else 0
        print(f"     {app:<20}: {pct_on:.3f}% ON | max={max_val:.0f}W | mean_ON={mean_on:.0f}W")

    return df


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — NORMALISATION
# ══════════════════════════════════════════════════════════════════════════════

def build_and_fit_scalers(df_train, config):
    agg_col = config["aggregate_col"]
    targets = config["target_appliances"]
    extras  = [c for c in config["extra_features"] if c in df_train.columns]

    scaler_agg = StandardScaler()
    scaler_agg.fit(df_train[[agg_col]])

    scaler_extra = None
    if extras:
        scaler_extra = MinMaxScaler()
        scaler_extra.fit(df_train[extras])

    scaler_targets = {}
    for app in targets:
        sc = MinMaxScaler()
        sc.fit(df_train[[app]])
        scaler_targets[app] = sc

    return {
        "agg":        scaler_agg,
        "extra":      scaler_extra,
        "targets":    scaler_targets,
        "extras_cols": extras,
    }


def compute_on_thresholds_norm(scalers, config):
    thr_norm = {}
    for app in config["target_appliances"]:
        sc  = scalers["targets"][app]
        raw = np.array([[config["on_thresholds"][app]]])
        thr_norm[app] = float(sc.transform(raw)[0, 0])
    return thr_norm


def scale_df(df, scalers, config):
    agg_col = config["aggregate_col"]
    targets = config["target_appliances"]
    extras  = scalers["extras_cols"]

    X_agg = scalers["agg"].transform(df[[agg_col]].values)

    if extras and scalers["extra"] is not None:
        X_extra = scalers["extra"].transform(df[extras].values)
        X = np.hstack([X_agg, X_extra]).astype(np.float32)
    else:
        X = X_agg.astype(np.float32)

    y_cols = [scalers["targets"][app].transform(df[[app]].values) for app in targets]
    y = np.hstack(y_cols).astype(np.float32)
    return X, y


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — GÉNÉRATEUR AVEC SURÉCHANTILLONNAGE
# ══════════════════════════════════════════════════════════════════════════════

class Seq2PointGenerator(tf.keras.utils.Sequence):
    """VERSION CAUSALE : la fenetre de `window_size` echantillons se termine
    PILE sur l'index cible (aucun echantillon futur utilise) -- contrairement
    a la version centree originale qui regardait window_size//2 pas en avant.
    Ce choix supprime le delai d'attente de ~window_size//2 * periode_echantillonnage
    necessaire en inference temps reel, au prix d'un contexte legerement plus
    pauvre (pas de "vision du futur" pour aider la decision)."""

    def __init__(self, X, y, window_size, stride, batch_size,
                 thr_norm, oversample_ratios, appliance_names, shuffle=True):
        self.X         = X
        self.y         = y
        self.w         = window_size
        self.stride    = stride
        self.batch_size = batch_size
        self.shuffle   = shuffle

        # Causal : le premier centre valide est window_size-1 (assez d'historique
        # disponible), le dernier est len(X)-1 (pas besoin de marge apres).
        centers_base = np.arange(self.w - 1, len(X), stride)

        extra = []
        for i, app in enumerate(appliance_names):
            ratio = oversample_ratios[app]
            if ratio <= 1:
                continue
            on_mask    = y[centers_base, i] > thr_norm[app]
            on_centers = centers_base[on_mask]
            if len(on_centers) > 0:
                extra.append(np.tile(on_centers, ratio - 1))

        self.centers = np.concatenate([centers_base] + extra) if extra else centers_base
        self.n = len(self.centers)
        self.on_epoch_end()

    def __len__(self):
        return int(np.ceil(self.n / self.batch_size))

    def on_epoch_end(self):
        self.indices = np.arange(self.n)
        if self.shuffle:
            np.random.shuffle(self.indices)

    def __getitem__(self, idx):
        batch_idx = self.indices[idx * self.batch_size: (idx + 1) * self.batch_size]
        centers   = self.centers[batch_idx]
        # Fenetre causale : les w echantillons se terminent AU centre inclus,
        # aucun echantillon apres c n'est utilise.
        X_batch   = np.stack([self.X[c - self.w + 1: c + 1] for c in centers])
        y_batch   = self.y[centers]
        return X_batch, y_batch


def make_generators(X, y, scalers, config):
    n = len(X)
    n_test  = int(n * config["test_split"])
    n_val   = int(n * config["val_split"])
    n_train = n - n_val - n_test

    X_train, y_train = X[:n_train],              y[:n_train]
    X_val,   y_val   = X[n_train:n_train+n_val], y[n_train:n_train+n_val]
    X_test,  y_test  = X[n_train+n_val:],        y[n_train+n_val:]

    w    = config["window_size"]
    s    = config["stride"]
    bs   = config["batch_size"]
    apps = config["target_appliances"]
    over = config["oversample_ratio"]
    no_over = {a: 1 for a in apps}

    thr_norm = compute_on_thresholds_norm(scalers, config)

    print(f"\n✂️  Split Train/Val/Test :")
    print(f"  Train brut : {n_train:,} | Val : {n_val:,} | Test : {n_test:,}")

    gen_train = Seq2PointGenerator(X_train, y_train, w, s, bs, thr_norm, over,    apps, shuffle=True)
    gen_val   = Seq2PointGenerator(X_val,   y_val,   w, s, bs, thr_norm, no_over, apps, shuffle=False)
    gen_test  = Seq2PointGenerator(X_test,  y_test,  w, 1, bs, thr_norm, no_over, apps, shuffle=False)

    print(f"  Train après suréchantillonnage : {gen_train.n:,} fenêtres")

    return gen_train, gen_val, gen_test, (X_test, y_test)


def generator_to_tf_dataset(gen, window_size, n_features, n_targets):
    def py_gen():
        for i in range(len(gen)):
            xb, yb = gen[i]
            yield xb, yb

    return tf.data.Dataset.from_generator(
        py_gen,
        output_signature=(
            tf.TensorSpec(shape=(None, window_size, n_features), dtype=tf.float32),
            tf.TensorSpec(shape=(None, n_targets),               dtype=tf.float32),
        )
    ).prefetch(tf.data.AUTOTUNE)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — LOSS PONDÉRÉE
# ══════════════════════════════════════════════════════════════════════════════

def weighted_huber_loss(thr_norm_list, weights_on, weights_off):
    thr  = tf.constant(thr_norm_list, dtype=tf.float32)
    w_on = tf.constant(weights_on,   dtype=tf.float32)
    w_off= tf.constant(weights_off,  dtype=tf.float32)

    def loss_fn(y_true, y_pred):
        is_on   = tf.cast(y_true > thr, tf.float32)
        weights = is_on * w_on + (1.0 - is_on) * w_off
        err     = y_true - y_pred
        huber   = tf.where(
            tf.abs(err) <= 1.0,
            0.5 * tf.square(err),
            tf.abs(err) - 0.5
        )
        return tf.reduce_mean(weights * huber)

    return loss_fn


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — ARCHITECTURE AVEC TÊTES SÉPARÉES
# ══════════════════════════════════════════════════════════════════════════════

def build_model(window_size, n_features, n_targets, lr, thr_norm_list, config):
    """
    Architecture avec tronc partagé + tête Dense séparée par appareil.

    Avantage : chaque appareil dispose de son propre sous-réseau
    de décision → spécialisation sans interférence entre appareils.

    Tronc : Conv1D → LSTM → LSTM  (features partagées)
    Têtes : Dense(64) → Dense(32) → Dense(1) × n_appareils
    """
    inp = layers.Input(shape=(window_size, n_features), name="agg_window")

    # ── Tronc partagé
    x = layers.Conv1D(32, 5, padding="causal", activation="relu")(inp)
    x = layers.BatchNormalization()(x)
    x = layers.Conv1D(64, 3, padding="causal", activation="relu")(x)
    x = layers.BatchNormalization()(x)

    x = layers.LSTM(128, return_sequences=True, dropout=0.2)(x)
    x = layers.LayerNormalization()(x)
    x = layers.LSTM(64, return_sequences=False, dropout=0.2)(x)

    shared = layers.Dense(128, activation="relu",
                          kernel_regularizer=regularizers.l2(1e-4))(x)
    shared = layers.Dropout(0.25)(shared)

    # ── Têtes séparées par appareil
    outputs = []
    for app in config["target_appliances"]:
        h = layers.Dense(64, activation="relu", name=f"head1_{app}")(shared)
        h = layers.Dropout(0.2)(h)
        h = layers.Dense(32, activation="relu", name=f"head2_{app}")(h)
        out = layers.Dense(1, activation="relu", name=f"out_{app}")(h)
        outputs.append(out)

    # Concaténer les sorties (B, n_targets)
    final_out = layers.Concatenate(name="appliance_power")(outputs)

    model = models.Model(inp, final_out, name="Seq2Point_v4_MultiHead")

    thr_norm_list_vals = [thr_norm_list[app] for app in config["target_appliances"]]

    loss_fn = weighted_huber_loss(
        thr_norm_list_vals,
        config["loss_weights_on"],
        config["loss_weights_off"],
    )

    model.compile(
        optimizer=Adam(learning_rate=lr, clipnorm=1.0),
        loss=loss_fn,
        metrics=["mae", tf.keras.metrics.RootMeanSquaredError(name="rmse")],
    )
    return model


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — ENTRAÎNEMENT
# ══════════════════════════════════════════════════════════════════════════════

def train(model, gen_train, gen_val, config, n_features, n_targets):
    print(f"\n🚀 Entraînement — {config['epochs']} epochs | batch={config['batch_size']}")

    cbs = [
        callbacks.EarlyStopping(
            monitor="val_mae", patience=12,
            restore_best_weights=True, verbose=1
        ),
        callbacks.ModelCheckpoint(
            config["model_path"], monitor="val_mae",
            save_best_only=True, verbose=1
        ),
        callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5,
            patience=6, min_lr=1e-6, verbose=1
        ),
    ]

    w = config["window_size"]
    print("  ⚙️  Conversion en tf.data pipeline (AUTOTUNE)...")
    train_ds = generator_to_tf_dataset(gen_train, w, n_features, n_targets)
    val_ds   = generator_to_tf_dataset(gen_val,   w, n_features, n_targets)

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=config["epochs"],
        callbacks=cbs,
        verbose=1,
    )

    print(f"\n✅ Meilleur val_mae : {min(history.history['val_mae']):.4f}")
    return history


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — ÉVALUATION AVEC POST-TRAITEMENT
# ══════════════════════════════════════════════════════════════════════════════

def evaluate(model, gen_test, scalers, config):
    print("\n📊 Évaluation sur le jeu de test...")

    y_pred_list, y_true_list = [], []
    gen_test.shuffle = False

    for i in range(len(gen_test)):
        xb, yb = gen_test[i]
        pred   = model.predict(xb, verbose=0)
        y_pred_list.append(pred)
        y_true_list.append(yb)

    y_pred_norm = np.vstack(y_pred_list)
    y_true_norm = np.vstack(y_true_list)

    results = {}
    y_true_w_all, y_pred_w_all = [], []

    for i, app in enumerate(config["target_appliances"]):
        sc     = scalers["targets"][app]
        true_w = sc.inverse_transform(y_true_norm[:, i:i+1]).flatten()
        pred_w = sc.inverse_transform(y_pred_norm[:, i:i+1]).flatten()
        pred_w = np.clip(pred_w, 0, None)

        # Post-traitement : seuillage ON/OFF
    

        mae  = mean_absolute_error(true_w, pred_w)
        mse  = mean_squared_error(true_w, pred_w)
        rmse = np.sqrt(mse)
        sae  = abs(pred_w.sum() - true_w.sum()) / (true_w.sum() + 1e-8)

        results[app] = {
            "MAE (W)":  round(mae, 2),
            "RMSE (W)": round(rmse, 2),
            "MSE (W²)": round(mse, 2),
            "SAE (%)":  round(sae * 100, 2),
        }
        y_true_w_all.append(true_w)
        y_pred_w_all.append(pred_w)

    df_res = pd.DataFrame(results).T
    print("\n" + "─" * 58)
    print(df_res.to_string())
    print("─" * 58)
    df_res.to_csv(os.path.join(config["output_dir"], "results_v4.csv"))

    return df_res, np.array(y_true_w_all), np.array(y_pred_w_all)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — VISUALISATION
# ══════════════════════════════════════════════════════════════════════════════

def plot_all(history, y_true, y_pred, config):
    out    = config["output_dir"]
    apps   = config["target_appliances"]
    colors = ["#2196F3", "#4CAF50", "#FF5722", "#9C27B0"]

    # Courbes d'entraînement
    fig, axes = plt.subplots(1, 2, figsize=(14, 4))
    fig.suptitle("Entraînement Seq2Point LSTM v4 (multi-head)", fontweight="bold")
    for ax, (tr, val), title in zip(
        axes,
        [("loss", "val_loss"), ("mae", "val_mae")],
        ["Loss (Huber pondérée)", "MAE (normalisé)"]
    ):
        ax.plot(history.history[tr],  label="Train", color="#2196F3", lw=2)
        ax.plot(history.history[val], label="Val",   color="#FF5722", lw=2, ls="--")
        ax.set_title(title); ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out, "training_v4.png"), dpi=120, bbox_inches="tight")
    plt.close()

    # Prédictions vs réel
    n_pts = min(3000, y_true.shape[1])
    fig, axes = plt.subplots(len(apps), 1, figsize=(16, 4 * len(apps)))
    fig.suptitle("Prédictions vs Réalité (Watts) — v4", fontsize=14, fontweight="bold")
    for i, (ax, app) in enumerate(zip(axes, apps)):
        t = np.arange(n_pts)
        ax.fill_between(t, y_true[i, :n_pts], alpha=0.2, color=colors[i])
        ax.plot(t, y_true[i, :n_pts], color=colors[i], lw=0.8, label="Réel")
        ax.plot(t, y_pred[i, :n_pts], color="red", lw=1.0, ls="--",
                label="Prédit", alpha=0.85)
        mae_l = mean_absolute_error(y_true[i, :n_pts], y_pred[i, :n_pts])
        ax.set_title(f"{app.replace('_', ' ').title()}  —  MAE={mae_l:.1f} W")
        ax.set_ylabel("Puissance (W)"); ax.legend(fontsize=9); ax.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(out, "predictions_v4.png"), dpi=120, bbox_inches="tight")
    plt.close()

    print(f"  💾 Graphiques → {out}")


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 62)
    print("  NILM — Seq2Point LSTM v4  (têtes séparées)")
    print("=" * 62)

    # 1. Chargement
    df = load_and_clean(CONFIG)

    # 2. Split temporel
    n = len(df)
    n_test  = int(n * CONFIG["test_split"])
    n_val   = int(n * CONFIG["val_split"])
    n_train = n - n_val - n_test
    df_train = df.iloc[:n_train]
    df_all   = df

    # 3. Scalers
    scalers = build_and_fit_scalers(df_train, CONFIG)

    # Sauvegarde des scalers -- necessaire pour reappliquer la meme normalisation
    # cote bridge Python / firmware F469 lors de l'inference en production.
    joblib.dump(scalers, CONFIG["scalers_path"])
    print(f"  💾 Scalers sauvegardes -> {CONFIG['scalers_path']}")

    # Export des constantes brutes en JSON (lisible sans Python/sklearn,
    # pratique pour le firmware C ou un script Python independant).
    scaler_constants = {
        "aggregate": {
            "type": "StandardScaler",
            "mean": float(scalers["agg"].mean_[0]),
            "scale": float(scalers["agg"].scale_[0]),
        },
        "extra_features": {
            "type": "MinMaxScaler",
            "columns": scalers["extras_cols"],
            "data_min": scalers["extra"].data_min_.tolist(),
            "data_max": scalers["extra"].data_max_.tolist(),
        },
        "targets": {
            app: {
                "type": "MinMaxScaler",
                "data_min": float(scalers["targets"][app].data_min_[0]),
                "data_max": float(scalers["targets"][app].data_max_[0]),
            }
            for app in CONFIG["target_appliances"]
        },
        "on_thresholds_watts": CONFIG["on_thresholds"],
    }
    json_path = CONFIG["scalers_path"].replace(".joblib", "_constants.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scaler_constants, f, indent=2)
    print(f"  💾 Constantes (JSON portable) -> {json_path}")

    # 4. Transformation
    X, y = scale_df(df_all, scalers, CONFIG)
    del df, df_train, df_all
    gc.collect()
    print(f"\n  X : {X.shape} | y : {y.shape}  —  RAM libérée ✅")

    # 5. Générateurs
    gen_train, gen_val, gen_test, _ = make_generators(X, y, scalers, CONFIG)

    # 6. Seuils normalisés pour la loss
    thr_norm_dict = compute_on_thresholds_norm(scalers, CONFIG)

    # 7. Modèle
    n_features = X.shape[1]
    n_targets  = y.shape[1]
    model = build_model(
        CONFIG["window_size"], n_features, n_targets,
        CONFIG["learning_rate"], thr_norm_dict, CONFIG
    )
    model.summary()

    # 8. Entraînement
    history = train(model, gen_train, gen_val, CONFIG, n_features, n_targets)

    # 9. Évaluation
    df_res, y_true_w, y_pred_w = evaluate(model, gen_test, scalers, CONFIG)

    # 10. Graphiques
    print("\n📈 Génération des graphiques...")
    plot_all(history, y_true_w, y_pred_w, CONFIG)

    print(f"\n🎉 Terminé ! Modèle → {CONFIG['model_path']}")
    return model, history, df_res


if __name__ == "__main__":
    main()