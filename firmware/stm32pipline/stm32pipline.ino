#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = "Synergie LAB";
const char* password = "Lab20232024";
const char* mqtt_broker = "broker.hivemq.com"; // IP du PC/broker
IPAddress   MQTT_BROKER_IP(18, 158, 142, 138);

const char* topic_to_stm32 = "nilm/packet/stm32F4stage"; // le PC publie ici les NilmSamplePkt bruts (65 octets)
#define NILM_PKT_SIZE 65

WiFiClient espClient;
PubSubClient mqtt(espClient);
HardwareSerial STM32Serial(2);

void mqttCallback(char* topic, byte* payload, unsigned int len) {
  Serial.print("MQTT recu, taille=");
  Serial.println(len);
  if (len != NILM_PKT_SIZE) {
    Serial.println("Taille incorrecte, paquet ignore");
    return;
  }
  STM32Serial.write(payload, len);
  Serial.println("Paquet transmis au STM32 via UART6");
}

void reconnectMQTT() {
  while (!mqtt.connected()) {
    Serial.print("Connexion MQTT...");
    if (mqtt.connect("ESP32NilmBridge")) {
      Serial.println(" connecte !");
      mqtt.subscribe(topic_to_stm32);
      Serial.print("Abonne au topic : ");
      Serial.println(topic_to_stm32);
    } else {
      Serial.print(" echec, code=");
      Serial.print(mqtt.state());
      Serial.println(" -- nouvelle tentative dans 2s");
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("=== Demarrage ESP32 NILM Bridge ===");

  STM32Serial.begin(115200, SERIAL_8N1, 16, 17);
  Serial.println("UART vers STM32 initialise (RX=16, TX=17)");

  WiFi.begin(ssid, password);
  Serial.print("Connexion WiFi");

  int tentatives = 0;
  while (WiFi.status() != WL_CONNECTED && tentatives < 30) {
    delay(500);
    Serial.print(".");
    tentatives++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connecte !");
    Serial.print("Adresse IP : ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nECHEC connexion WiFi apres 15s -- verifiez SSID/mot de passe");
    Serial.println("Le programme continue mais MQTT ne fonctionnera pas");
  }

  mqtt.setServer(MQTT_BROKER_IP, 1883);
  mqtt.setBufferSize(128);
  mqtt.setCallback(mqttCallback);

  Serial.println("=== Setup termine ===");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!mqtt.connected()) reconnectMQTT();
    mqtt.loop();
  }
}