"""
finetune_local.py
------------------
Fine-tuning du modele NILM pre-entraine (UK-DALE) sur des donnees LOCALES
etiquetees (agregat + puissance individuelle des 4 appareils).

Strategie : on GARDE les scalers existants tels quels (fit sur UK-DALE) --
tes valeurs mesurees (~150W total, fridge~94W, laptop~57W) rentrent dans les
plages deja vues a l'entrainement (data_max fridge=158W, laptop=100W), donc
pas besoin de refitter la normalisation, seulement les poids du reseau.

On gele le "tronc" (Conv1D + BatchNorm + 1ere LSTM) qui capture des motifs
temporels generaux, et on ne reentraine que la 2e LSTM + les tetes par
appareil -- adaptation ciblee, moins de risque de sur-apprentissage avec un
petit jeu de donnees local, entrainement plus rapide.

Prerequis : avoir execute prepare_local_dataset.py au prealable pour obtenir
un CSV avec les 13 features engineered.

Usage:
    python finetune_local.py \
        --local-csv local_AI_ready.csv \
        --base-model nilm_v5_causal_w49.keras \
        --scalers nilm_v5_causal_scalers.joblib \
        --epochs 20 --lr 5e-5
"""

import argparse
import os
import joblib
import numpy as np
import tensorflow as tf
from tensorflow.keras import optimizers

# Reutilise les fonctions du script d'entrainement causal original
from lstm_causal import (
    CONFIG, load_and_clean, scale_df, make_generators,
    generator_to_tf_dataset, weighted_huber_loss, compute_on_thresholds_norm,
    evaluate,
)


def freeze_trunk(model, freeze_up_to_layer_name="lstm"):
    """Gele toutes les couches jusqu'a (et y compris) la 1ere LSTM.
    Les couches suivantes (2e LSTM, Dense partages, tetes) restent
    entrainables. Affiche le statut final pour verification."""
    freezing = True
    n_lstm_seen = 0
    for layer in model.layers:
        if freezing:
            layer.trainable = False
        if "lstm" in layer.name.lower():
            n_lstm_seen += 1
            if n_lstm_seen >= 1:
                freezing = False  # a partir de la couche APRES cette LSTM, on degele

    print("\n🔒 Statut des couches :")
    for layer in model.layers:
        marker = "🔓 entrainable" if layer.trainable else "🔒 gelee"
        print(f"   {marker:16s} {layer.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-csv", required=True)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--scalers", required=True)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lr", type=float, default=5e-5, help="LR faible -- fine-tuning, pas from-scratch")
    parser.add_argument("--output", default="nilm_v6_finetuned.keras")
    args = parser.parse_args()

    # 1. Charger modele + scalers pre-entraines (INCHANGES)
    print(f"📦 Chargement du modele de base : {args.base_model}")
    model = tf.keras.models.load_model(args.base_model, compile=False)
    scalers = joblib.load(args.scalers)
    print(f"📦 Scalers charges depuis : {args.scalers}")

    # 2. Charger et normaliser les donnees locales (memes scalers, .transform() seulement)
    local_config = dict(CONFIG)
    local_config["data_path"] = args.local_csv
    local_config["output_dir"] = "nilm_results_finetune_local/"
    os.makedirs(local_config["output_dir"], exist_ok=True)
    df_local = load_and_clean(local_config)
    X_local, y_local = scale_df(df_local, scalers, local_config)
    print(f"✅ Donnees locales : {len(df_local):,} echantillons normalises")

    # 3. Generateurs (memes fonctions que l'entrainement original -- fenetre causale, oversampling)
    gen_train, gen_val, gen_test, (X_test, y_test) = make_generators(X_local, y_local, scalers, local_config)

    n_features = X_local.shape[1]
    n_targets = len(local_config["target_appliances"])
    w = local_config["window_size"]

    ds_train = generator_to_tf_dataset(gen_train, w, n_features, n_targets)
    ds_val = generator_to_tf_dataset(gen_val, w, n_features, n_targets)

    # 4. Geler le tronc, ne fine-tuner que la 2e LSTM + les tetes
    freeze_trunk(model)

    thr_norm = compute_on_thresholds_norm(scalers, local_config)
    thr_norm_list = [thr_norm[a] for a in local_config["target_appliances"]]

    loss_fn = weighted_huber_loss(
        thr_norm_list,
        local_config["loss_weights_on"],
        local_config["loss_weights_off"],
    )
    model.compile(optimizer=optimizers.Adam(learning_rate=args.lr), loss=loss_fn)

    # 5. Fine-tuning
    print(f"\n🚀 Fine-tuning ({args.epochs} epochs, lr={args.lr}) ...")
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, min_lr=1e-7),
    ]
    model.fit(ds_train, validation_data=ds_val, epochs=args.epochs, callbacks=callbacks)

    # 6. Evaluation sur le jeu de test local (mis de cote, jamais vu pendant le fine-tuning)
    print("\n📊 Evaluation sur donnees locales de test :")
    evaluate(model, gen_test, scalers, local_config)

    # 7. Sauvegarde -- MEMES scalers que le modele de base (non modifies)
    model.save(args.output)
    print(f"\n💾 Modele fine-tune sauvegarde -> {args.output}")
    print("   (les scalers restent inchanges, reutilise le meme .joblib/.json qu'avant)")


if __name__ == "__main__":
    main()
