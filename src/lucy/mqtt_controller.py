"""MQTT controller with multi-device discovery support."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
from loguru import logger

from .config import settings
from .device_manager import DeviceManager


class MQTTController:
    """Publish commands + subscribe to discovery/status from ESP32 nodes."""

    def __init__(
        self,
        device_manager: Optional[DeviceManager] = None,
        broker: Optional[str] = None,
        port: Optional[int] = None,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.broker = broker or settings.mqtt_broker
        self.port = port or settings.mqtt_port
        self.client_id = client_id or settings.mqtt_client_id
        self.username = username or settings.mqtt_username
        self.password = password or settings.mqtt_password

        self.device_manager = device_manager or DeviceManager()

        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self.client_id,
        )

        if self.username:
            self.client.username_pw_set(self.username, self.password)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            logger.success(f"MQTT connected to {self.broker}:{self.port}")
            client.subscribe(DeviceManager.DISCOVERY_TOPIC, qos=1)
            client.subscribe("lucy/+/devices/+/status", qos=0)
            logger.info("Subscribed to discovery & status topics")
        else:
            logger.error(f"MQTT connection failed: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        logger.warning(f"MQTT disconnected: {reason_code}")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            logger.warning(f"Invalid JSON on {topic}")
            return

        if topic == DeviceManager.DISCOVERY_TOPIC:
            self.device_manager.handle_discovery(payload)
            return

        parts = topic.split("/")
        if len(parts) >= 5 and parts[-1] == "status":
            device_id = parts[-2]
            self.device_manager.handle_status(device_id, payload)

    def connect(self) -> None:
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"MQTT connect error: {e}")
            raise

    def publish_action(
        self,
        device_id: str,
        command: str,
        value: Any = None,
        retain: bool = False,
    ) -> None:
        """Publish JSON command to the correct device topic."""
        topic = self.device_manager.topic_for(device_id)

        payload: Dict[str, Any] = {
            "state": command.upper() if isinstance(command, str) else command,
            "value": value,
            "source": "lucy",
            "ts": int(__import__("time").time()),
        }

        result = self.client.publish(
            topic,
            json.dumps(payload, ensure_ascii=False),
            qos=1,
            retain=retain,
        )

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.success(f"MQTT → {topic} | {payload}")
        else:
            logger.error(f"MQTT publish failed (rc={result.rc})")

    def request_discovery(self) -> None:
        """Ask all nodes to re-announce (optional broadcast)."""
        self.client.publish(
            "lucy/discovery/request",
            json.dumps({"source": "lucy"}),
            qos=0,
        )
        logger.info("Discovery request broadcast")

    def publish_raw(
        self, topic: str, payload: str, retain: bool = False, qos: int = 0
    ) -> None:
        """Low-level publish (used by HA discovery)."""
        self.client.publish(topic, payload, qos=qos, retain=retain)

    def publish_ha_discovery(self) -> int:
        """Publish Home Assistant MQTT discovery for all devices."""
        from .ha_discovery import HomeAssistantDiscovery

        ha = HomeAssistantDiscovery(
            device_manager=self.device_manager,
            mqtt_publish=lambda t, p, retain=True: self.publish_raw(
                t, p, retain=retain, qos=0
            ),
        )
        return ha.publish_all()

    def disconnect(self) -> None:
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT disconnected cleanly")
        except Exception:
            pass
