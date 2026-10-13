/**
 * Lucy ESP32 — Vehicle (EV) Node Example
 * PERINGATAN: Jangan hubungkan ke sistem safety-critical.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* WIFI_SSID      = "YOUR_CAR_HOTSPOT_OR_AP";
const char* WIFI_PASSWORD  = "YOUR_PASSWORD";
const char* MQTT_BROKER    = "192.168.4.1";
const int   MQTT_PORT      = 1883;

const char* NODE_ID        = "esp32-cabin-01";
const char* PROFILE        = "vehicle";
const char* FIRMWARE_VER   = "1.1.0-ev";

const char* MY_DEVICES[]   = {"lampu_kabin", "ac_mobil"};
const int   MY_DEVICE_COUNT = 2;

struct DevicePin {
  const char* deviceId;
  int pin;
  bool activeHigh;
};

DevicePin devicePins[] = {
  {"lampu_kabin", 5, true},
  {"ac_mobil", 18, true},
};
const int PIN_COUNT = sizeof(devicePins) / sizeof(devicePins[0]);
const unsigned long HEARTBEAT_MS = 20000;

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
unsigned long lastHeartbeat = 0;

int findPin(const char* deviceId) {
  for (int i = 0; i < PIN_COUNT; i++) {
    if (strcmp(devicePins[i].deviceId, deviceId) == 0) return i;
  }
  return -1;
}

void setDevice(const char* deviceId, bool on) {
  int idx = findPin(deviceId);
  if (idx < 0) return;
  bool level = devicePins[idx].activeHigh ? on : !on;
  digitalWrite(devicePins[idx].pin, level ? HIGH : LOW);
  Serial.printf("[EV] %s → %s\n", deviceId, on ? "ON" : "OFF");
}

void publishStatus(const char* deviceId, const char* state, int value = -1) {
  char topic[96];
  snprintf(topic, sizeof(topic), "lucy/%s/devices/%s/status", PROFILE, deviceId);
  StaticJsonDocument<192> doc;
  doc["state"] = state;
  if (value >= 0) doc["value"] = value;
  doc["node_id"] = NODE_ID;
  doc["online"] = true;
  char buf[192];
  serializeJson(doc, buf);
  mqtt.publish(topic, buf, false);
}

void announceDiscovery() {
  StaticJsonDocument<384> doc;
  doc["node_id"] = NODE_ID;
  doc["profile"] = PROFILE;
  doc["fw"] = FIRMWARE_VER;
  doc["ip"] = WiFi.localIP().toString();
  JsonArray arr = doc.createNestedArray("devices");
  for (int i = 0; i < MY_DEVICE_COUNT; i++) arr.add(MY_DEVICES[i]);
  char buf[384];
  serializeJson(doc, buf);
  mqtt.publish("lucy/discovery/announce", buf, false);
}

void handleCommand(const char* deviceId, const char* state, JsonVariant value) {
  if (strcmp(state, "SET_TEMP") == 0 || strcmp(state, "SET_FAN") == 0 ||
      strcmp(state, "SET_POSITION") == 0 || strcmp(state, "SET_BEAM") == 0) {
    int v = value.isNull() ? 0 : value.as<int>();
    setDevice(deviceId, true);
    publishStatus(deviceId, state, v);
    return;
  }
  bool on = (strcmp(state, "ON") == 0 || strcmp(state, "OPEN") == 0 || strcmp(state, "UNLOCK") == 0);
  if (strcmp(state, "OFF") == 0 || strcmp(state, "CLOSE") == 0 || strcmp(state, "LOCK") == 0) on = false;
  setDevice(deviceId, on);
  publishStatus(deviceId, on ? "ON" : "OFF");
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, payload, length)) return;
  if (strcmp(topic, "lucy/discovery/request") == 0) { announceDiscovery(); return; }
  String t = String(topic);
  int start = t.indexOf("/devices/") + 9;
  int end = t.indexOf("/set");
  if (start < 9 || end < 0) return;
  handleCommand(t.substring(start, end).c_str(), doc["state"] | "", doc["value"]);
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < PIN_COUNT; i++) {
    pinMode(devicePins[i].pin, OUTPUT);
    digitalWrite(devicePins[i].pin, LOW);
  }
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) delay(400);
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
}

void loop() {
  if (!mqtt.connected()) {
    if (mqtt.connect(NODE_ID)) {
      for (int i = 0; i < MY_DEVICE_COUNT; i++) {
        char topic[96];
        snprintf(topic, sizeof(topic), "lucy/%s/devices/%s/set", PROFILE, MY_DEVICES[i]);
        mqtt.subscribe(topic);
      }
      mqtt.subscribe("lucy/discovery/request");
      announceDiscovery();
    } else delay(4000);
  }
  mqtt.loop();
  if (millis() - lastHeartbeat > HEARTBEAT_MS) {
    lastHeartbeat = millis();
    for (int i = 0; i < MY_DEVICE_COUNT; i++) publishStatus(MY_DEVICES[i], "online");
  }
}
