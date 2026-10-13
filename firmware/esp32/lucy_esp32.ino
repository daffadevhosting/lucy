/**
 * Lucy ESP32 Firmware (legacy single-board)
 * Prefer lucy_node.ino for multi-node setups.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* MQTT_BROKER   = "192.168.1.100";
const int   MQTT_PORT     = 1883;
const char* CLIENT_ID     = "lucy-esp32-01";

const int PIN_LAMPU_TERAS = 5;
const int PIN_RELAY_1 = 21;
const int PIN_RELAY_2 = 22;

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

void setRelay(int pin, bool on) {
  digitalWrite(pin, on ? HIGH : LOW);
  Serial.printf("GPIO %d → %s\n", pin, on ? "ON" : "OFF");
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, payload, length)) return;

  String t = String(topic);
  int start = t.indexOf("devices/") + 8;
  int end = t.indexOf("/set");
  if (start < 8 || end < 0) return;
  String deviceId = t.substring(start, end);
  const char* state = doc["state"] | "";
  bool on = (strcmp(state, "ON") == 0);

  if (deviceId == "lampu_teras") setRelay(PIN_LAMPU_TERAS, on);
  else if (deviceId == "relay_1") setRelay(PIN_RELAY_1, on);
  else if (deviceId == "relay_2") setRelay(PIN_RELAY_2, on);
}

void setup() {
  pinMode(PIN_LAMPU_TERAS, OUTPUT);
  pinMode(PIN_RELAY_1, OUTPUT);
  pinMode(PIN_RELAY_2, OUTPUT);
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
}

void loop() {
  if (!mqtt.connected()) {
    if (mqtt.connect(CLIENT_ID)) {
      mqtt.subscribe("lucy/+/devices/+/set");
      mqtt.subscribe("home/devices/+/set");
    } else delay(5000);
  }
  mqtt.loop();
}
