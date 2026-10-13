/**
 * Lucy ESP32 Node Firmware (Multi-room / Multi-node)
 * - Announces itself on boot + heartbeat (discovery)
 * - Subscribes only to devices it owns
 * - Publishes status / heartbeat
 *
 * Topics:
 *   lucy/discovery/announce
 *   lucy/discovery/request
 *   lucy/{profile}/devices/{device_id}/set
 *   lucy/{profile}/devices/{device_id}/status
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* WIFI_SSID      = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD  = "YOUR_WIFI_PASSWORD";
const char* MQTT_BROKER    = "192.168.1.100";
const int   MQTT_PORT      = 1883;
const char* MQTT_USER      = "";
const char* MQTT_PASS      = "";

const char* NODE_ID        = "esp32-teras-01";
const char* PROFILE        = "home";
const char* FIRMWARE_VER   = "1.1.0";

const char* MY_DEVICES[]   = {"lampu_teras"};
const int   MY_DEVICE_COUNT = 1;

struct DevicePin {
  const char* deviceId;
  int pin;
  bool activeHigh;
};

DevicePin devicePins[] = {
  {"lampu_teras", 5, true},
};
const int PIN_COUNT = sizeof(devicePins) / sizeof(devicePins[0]);
const unsigned long HEARTBEAT_MS = 30000;

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
  Serial.printf("[GPIO] %s → %s\n", deviceId, on ? "ON" : "OFF");
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
  Serial.println("[Discovery] Announced");
}

void handleCommand(const char* deviceId, const char* state, JsonVariant value) {
  Serial.printf("[CMD] %s → %s\n", deviceId, state);
  bool on = (strcmp(state, "ON") == 0 || strcmp(state, "OPEN") == 0 || strcmp(state, "UNLOCK") == 0);
  if (strcmp(state, "OFF") == 0 || strcmp(state, "CLOSE") == 0 || strcmp(state, "LOCK") == 0) on = false;
  if (strncmp(state, "SET_", 4) == 0) {
    int v = value.isNull() ? 0 : value.as<int>();
    setDevice(deviceId, v > 0);
    publishStatus(deviceId, state, v);
    return;
  }
  setDevice(deviceId, on);
  publishStatus(deviceId, on ? "ON" : "OFF");
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, payload, length)) return;
  if (strcmp(topic, "lucy/discovery/request") == 0) {
    announceDiscovery();
    return;
  }
  String t = String(topic);
  int start = t.indexOf("/devices/") + 9;
  int end = t.indexOf("/set");
  if (start < 9 || end < 0) return;
  String deviceId = t.substring(start, end);
  handleCommand(deviceId.c_str(), doc["state"] | "", doc["value"]);
}

void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(400); Serial.print("."); }
  Serial.printf("\nIP: %s\n", WiFi.localIP().toString().c_str());
}

void reconnectMQTT() {
  while (!mqtt.connected()) {
    Serial.print("MQTT...");
    bool ok = (strlen(MQTT_USER) > 0)
                  ? mqtt.connect(NODE_ID, MQTT_USER, MQTT_PASS)
                  : mqtt.connect(NODE_ID);
    if (ok) {
      Serial.println("OK");
      for (int i = 0; i < MY_DEVICE_COUNT; i++) {
        char topic[96];
        snprintf(topic, sizeof(topic), "lucy/%s/devices/%s/set", PROFILE, MY_DEVICES[i]);
        mqtt.subscribe(topic);
      }
      mqtt.subscribe("lucy/discovery/request");
      announceDiscovery();
    } else {
      Serial.printf("fail rc=%d\n", mqtt.state());
      delay(4000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.printf("\n=== Lucy Node %s (%s) ===\n", NODE_ID, PROFILE);
  for (int i = 0; i < PIN_COUNT; i++) {
    pinMode(devicePins[i].pin, OUTPUT);
    digitalWrite(devicePins[i].pin, devicePins[i].activeHigh ? LOW : HIGH);
  }
  setupWiFi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
}

void loop() {
  if (!mqtt.connected()) reconnectMQTT();
  mqtt.loop();
  if (millis() - lastHeartbeat > HEARTBEAT_MS) {
    lastHeartbeat = millis();
    for (int i = 0; i < MY_DEVICE_COUNT; i++) publishStatus(MY_DEVICES[i], "online");
  }
}
