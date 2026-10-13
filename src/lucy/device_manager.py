"""Multi-room / multi-ESP32 device registry + MQTT discovery."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger

from .config import DEVICES_PATH, settings


@dataclass
class LiveDevice:
    """Runtime state of a discovered or configured device."""

    device_id: str
    name: str
    type: str
    room_or_zone: str
    node_id: str
    mqtt_topic: str
    commands: List[str]
    online: bool = False
    last_seen: Optional[float] = None
    state: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        self.last_seen = time.time()
        self.online = True

    def mark_offline(self) -> None:
        self.online = False


class DeviceManager:
    """Central registry for multi-room (home) or multi-zone (vehicle) devices."""

    DISCOVERY_TOPIC = "lucy/discovery/announce"
    STATUS_TOPIC = "lucy/+/devices/+/status"
    HEARTBEAT_TIMEOUT = 90

    def __init__(self) -> None:
        self.profile: str = "home"
        self.devices: Dict[str, LiveDevice] = {}
        self.rooms_or_zones: Dict[str, str] = {}
        self._load_static_config()

    def _load_static_config(self) -> None:
        if not DEVICES_PATH.exists():
            logger.warning(f"devices.yaml not found at {DEVICES_PATH}")
            return
        with open(DEVICES_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self.profile = data.get("profile", "home")

        if self.profile == "vehicle":
            device_section = data.get("vehicle_devices", {})
            zone_section = data.get("vehicle_zones", {})
            self.rooms_or_zones = {k: v.get("name", k) for k, v in zone_section.items()}
            location_key = "zone"
        else:
            device_section = data.get("devices", {})
            room_section = data.get("rooms", {})
            self.rooms_or_zones = {k: v.get("name", k) for k, v in room_section.items()}
            location_key = "room"

        for did, info in device_section.items():
            loc = info.get(location_key) or info.get("room") or info.get("zone") or "unknown"
            self.devices[did] = LiveDevice(
                device_id=did,
                name=info.get("name", did),
                type=info.get("type", "relay"),
                room_or_zone=loc,
                node_id=info.get("node_id", "unknown"),
                mqtt_topic=info.get("mqtt_topic", f"lucy/{self.profile}/devices/{did}/set"),
                commands=info.get("commands", ["ON", "OFF"]),
                meta=info,
            )

        logger.info(
            f"DeviceManager loaded profile={self.profile} | "
            f"{len(self.devices)} devices | {len(self.rooms_or_zones)} rooms/zones"
        )

    def handle_discovery(self, payload: Dict[str, Any]) -> None:
        node_id = payload.get("node_id")
        if not node_id:
            return
        for did in payload.get("devices", []):
            if did in self.devices:
                self.devices[did].touch()
                self.devices[did].meta["fw"] = payload.get("fw")
                self.devices[did].meta["ip"] = payload.get("ip")
                logger.success(f"Discovery: {did} online via {node_id}")

    def handle_status(self, device_id: str, payload: Dict[str, Any]) -> None:
        if device_id not in self.devices:
            return
        dev = self.devices[device_id]
        dev.touch()
        if "state" in payload:
            st = payload["state"]
            dev.state.update(st if isinstance(st, dict) else {"value": st})
        else:
            dev.state.update(payload)

    def check_timeouts(self) -> None:
        now = time.time()
        for dev in self.devices.values():
            if dev.last_seen and (now - dev.last_seen) > self.HEARTBEAT_TIMEOUT:
                if dev.online:
                    logger.warning(f"Device offline (timeout): {dev.device_id}")
                dev.mark_offline()

    def get(self, device_id: str) -> Optional[LiveDevice]:
        return self.devices.get(device_id)

    def list_online(self) -> List[LiveDevice]:
        return [d for d in self.devices.values() if d.online]

    def list_by_room(self, room: str) -> List[LiveDevice]:
        return [d for d in self.devices.values() if d.room_or_zone == room]

    def list_for_llm(self) -> str:
        lines = []
        by_loc: Dict[str, List[LiveDevice]] = {}
        for d in self.devices.values():
            by_loc.setdefault(d.room_or_zone, []).append(d)
        for loc, devices in sorted(by_loc.items()):
            loc_name = self.rooms_or_zones.get(loc, loc)
            lines.append(f"[{loc_name}]")
            for d in devices:
                status = "online" if d.online else "configured"
                cmds = ", ".join(d.commands)
                lines.append(f"  - {d.device_id}: {d.name} ({d.type}) → [{cmds}] ({status})")
        return "\n".join(lines) if lines else "Belum ada perangkat terdaftar."

    def validate_action(self, device_id: str, command: str) -> bool:
        dev = self.devices.get(device_id)
        if not dev:
            return False
        return command.upper() in [c.upper() for c in dev.commands]

    def topic_for(self, device_id: str) -> str:
        dev = self.devices.get(device_id)
        if dev:
            return dev.mqtt_topic
        return f"lucy/{self.profile}/devices/{device_id}/set"
