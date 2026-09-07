import tensorflow as tf

model = tf.keras.models.load_model("nilm_v5_causal_w49.keras", compile=False)
config = model.get_config()

def force_unroll(layer_cfg):
    cls = layer_cfg.get("class_name", "")
    if cls in ("LSTM", "Bidirectional"):
        if cls == "LSTM":
            layer_cfg["config"]["unroll"] = True
            layer_cfg["config"]["dropout"] = 0.0
            layer_cfg["config"]["recurrent_dropout"] = 0.0
        elif cls == "Bidirectional":
            inner = layer_cfg["config"]["layer"]["config"]
            inner["unroll"] = True
            inner["dropout"] = 0.0
            inner["recurrent_dropout"] = 0.0

for layer_cfg in config["layers"]:
    force_unroll(layer_cfg)

model_unrolled = tf.keras.Model.from_config(config)
model_unrolled.set_weights(model.get_weights())
model_unrolled.summary()

converter = tf.lite.TFLiteConverter.from_keras_model(model_unrolled)
tflite_model = converter.convert()

with open("nilm_lstm_fp32.tflite", "wb") as f:
    f.write(tflite_model)

print("Conversion OK, wrote nilm_lstm_fp32.tflite")