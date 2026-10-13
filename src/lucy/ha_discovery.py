"""Home Assistant MQTT Discovery publisher."""

from __future__ import annotations

import json
from typing import Any, Dict

from loguru import logger

from .device_manager import DeviceManager, LiveDevice

TYPE_MAP = {
    "relay": "switch",
    "light": "light",
    "headlight": "light",
    "fan": "fan",
    "ac": "climate",
    "climate": "climate",
    "lock": "lock",
    "window": "cover",
    "power": "switch",
}


class HomeAssistantDiscovery:
    """Publish MQTT discovery messages for Home Assistant."""

    def __init__(self, device_manager: DeviceManager, mqtt_publish, discovery_prefix: str = "homeassistant") -> None:
        self.dm = device_manager
        self.publish = mqtt_publish
        self.prefix = discovery_prefix

    def _component_for(self, dev: LiveDevice) -> str:
        return TYPE_MAP.get(dev.type.lower(), "switch")

    def _config_payload(self, dev: LiveDevice) -> Dict[str, Any]:
        component = self._component_for(dev)
        unique_id = f"lucy_{dev.device_id}"
        cmd_topic = dev.mqtt_topic
        state_topic = dev.mqtt_topic.replace("/set", "/status")

        base: Dict[str, Any] = {
            "name": dev.name,
            "unique_id": unique_id,
            "command_topic": cmd_topic,
            "state_topic": state_topic,
            "availability_topic": state_topic,
            "payload_available": "online",
            "payload_not_available": "offline",
            "device": {
                "identifiers": [f"lucy_{dev.node_id}"],
                "name": f"Lucy Node {dev.node_id}",
                "manufacturer": "Lucy IoT",
                "model": "ESP32 Node",
                "sw_version": "1.1",
            },
            "json_attributes_topic": state_topic,
        }

        if component in ("switch", "light"):
            base.update({
                "payload_on": json.dumps({"state": "ON", "source": "ha"}),
                "payload_off": json.dumps({"state": "OFF", "source": "ha"}),
                "state_on": "ON",
                "state_off": "OFF",
                "value_template": "{{ value_json.state | default(value_json.value) }}",
            })
        elif component == "lock":
            base.update({
                "payload_lock": json.dumps({"state": "LOCK", "source": "ha"}),
                "payload_unlock": json.dumps({"state": "UNLOCK", "source": "ha"}),
                "state_locked": "LOCK",
                "state_unlocked": "UNLOCK",
                "value_template": "{{ value_json.state }}",
            })
        elif component == "fan":
            base.update({
                "payload_on": json.dumps({"state": "ON", "source": "ha"}),
                "payload_off": json.dumps({"state": "OFF", "source": "ha"}),
                "percentage_command_topic": cmd_topic,
                "percentage_command_template": '{"state":"SET_SPEED","value":{{ value }},"source":"ha"}',
            })
        elif component == "climate":
            base.update({
                "mode_command_topic": cmd_topic,
                "temperature_command_topic": cmd_topic,
                "modes": ["off", "cool", "auto"],
                "min_temp": 16,
                "max_temp": 30,
                "temp_step": 1,
                "mode_command_template": '{% if value == "off" %}{"state":"OFF","source":"ha"}{% else %}{"state":"ON","source":"ha"}{% endif %}',
                "temperature_command_template": '{"state":"SET_TEMP","value":{{ value }},"source":"ha"}',
            })
        elif component == "cover":
            base.update({
                "payload_open": json.dumps({"state": "OPEN", "source": "ha"}),
                "payload_close": json.dumps({"state": "CLOSE", "source": "ha"}),
                "payload_stop": json.dumps({"state": "STOP", "source": "ha"}),
                "position_topic": state_topic,
                "set_position_topic": cmd_topic,
                "set_position_template": '{"state":"SET_POSITION","value":{{ position }},"source":"ha"}',
            })

        return base

    def publish_all(self) -> int:
        count = 0
        for dev in self.dm.devices.values():
            component = self._component_for(dev)
            topic = f"{self.prefix}/{component}/lucy_{dev.device_id}/config"
            payload = self._config_payload(dev)
            self.publish(topic, json.dumps(payload), retain=True)
            count += 1
            logger.debug(f"HA discovery → {topic}")
        logger.success(f"Home Assistant discovery published for {count} devices")
        return count

    def unpublish_all(self) -> None:
        for dev in self.dm.devices.values():
            component = self._component_for(dev)
            topic = f"{self.prefix}/{component}/lucy_{dev.device_id}/config"
            self.publish(topic, "", retain=True)
        logger.info("HA discovery cleared")
