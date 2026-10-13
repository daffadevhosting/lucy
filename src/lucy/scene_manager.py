"""Scene & group command executor."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger

from .config import ROOT_DIR
from .device_manager import DeviceManager, LiveDevice

SCENES_PATH = ROOT_DIR / "config" / "scenes.yaml"


class SceneManager:
    """Load scenes/groups and resolve them to device actions."""

    def __init__(self, device_manager: DeviceManager) -> None:
        self.dm = device_manager
        self.scenes: Dict[str, Dict[str, Any]] = {}
        self.groups: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not SCENES_PATH.exists():
            logger.warning(f"scenes.yaml not found: {SCENES_PATH}")
            return
        with open(SCENES_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self.scenes = data.get("scenes", {})
        self.groups = data.get("groups", {})
        logger.info(f"Loaded {len(self.scenes)} scenes, {len(self.groups)} groups")

    def list_for_llm(self) -> str:
        lines = ["Scenes:"]
        for sid, info in self.scenes.items():
            lines.append(f"  - {sid}: {info.get('name')} — {info.get('description', '')}")
        lines.append("Groups:")
        for gid, info in self.groups.items():
            lines.append(f"  - {gid}: {info.get('name')}")
        return "\n".join(lines)

    def get_scene_actions(self, scene_id: str) -> List[Dict[str, Any]]:
        scene = self.scenes.get(scene_id)
        if not scene:
            return []
        return list(scene.get("actions", []))

    def resolve_group(
        self,
        group_id: str,
        command: str,
        value: Any = None,
    ) -> List[Dict[str, Any]]:
        """
        Expand a group into individual device actions.
        Example: group=semua_lampu, command=OFF → all matching lights OFF
        """
        group = self.groups.get(group_id)
        if not group:
            return []

        match = group.get("match", {})
        types = [t.lower() for t in match.get("type", [])]
        rooms = match.get("room") or match.get("zone") or []

        actions = []
        for dev in self.dm.devices.values():
            type_ok = (not types) or (dev.type.lower() in types)
            room_ok = (not rooms) or (dev.room_or_zone in rooms)
            if type_ok and room_ok:
                if command.upper() in [c.upper() for c in dev.commands]:
                    actions.append(
                        {
                            "device_id": dev.device_id,
                            "command": command.upper(),
                            "value": value,
                        }
                    )
        return actions

    def resolve(
        self,
        action_type: str,
        scene_id: Optional[str] = None,
        group_id: Optional[str] = None,
        command: Optional[str] = None,
        value: Any = None,
    ) -> List[Dict[str, Any]]:
        if action_type == "scene_action" and scene_id:
            return self.get_scene_actions(scene_id)
        if action_type == "group_action" and group_id and command:
            return self.resolve_group(group_id, command, value)
        return []
