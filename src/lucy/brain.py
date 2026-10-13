"""AI Brain — LLM with structured JSON output for IoT decisions."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from loguru import logger
from openai import OpenAI

from .config import settings
from .device_manager import DeviceManager
from .scene_manager import SceneManager


SYSTEM_PROMPT_HOME = """
Kamu adalah Lucy, asisten rumah pintar berbahasa Indonesia yang ramah, singkat, dan cerdas.
Kamu mengontrol perangkat di berbagai ruangan, scene, dan group.

Kamu HARUS selalu mengembalikan HANYA JSON valid dengan skema berikut:

{{
  "type": "iot_action" | "scene_action" | "group_action" | "conversational",
  "device_id": string | null,
  "scene_id": string | null,
  "group_id": string | null,
  "command": "ON" | "OFF" | "SET_SPEED" | "SET_TEMP" | "LOCK" | "UNLOCK" | "OPEN" | "CLOSE" | null,
  "value": number | string | null,
  "speech_response": string
}}

Aturan ketat:
1. Kontrol satu perangkat → type = "iot_action" + device_id + command
2. Scene / mode (mode malam, mode pagi, semua mati, mode tamu) → type = "scene_action" + scene_id
3. Group (semua lampu, semua AC, lampu di satu ruangan) → type = "group_action" + group_id + command
4. Ngobrol biasa → type = "conversational"
5. ID harus cocok dengan daftar di bawah. Jika tidak yakin, set null.
6. speech_response selalu diisi, singkat dan natural dalam bahasa Indonesia.
7. Jangan pernah mengembalikan teks di luar JSON.

Daftar perangkat (per ruangan):
{devices_list}

Daftar scene & group:
{scenes_list}
"""

SYSTEM_PROMPT_VEHICLE = """
Kamu adalah Lucy, asisten suara mobil EV berbahasa Indonesia yang ramah, singkat, dan fokus keselamatan.

Kamu HARUS selalu mengembalikan HANYA JSON valid dengan skema berikut:

{{
  "type": "iot_action" | "scene_action" | "group_action" | "conversational",
  "device_id": string | null,
  "scene_id": string | null,
  "group_id": string | null,
  "command": "ON" | "OFF" | "SET_TEMP" | "SET_FAN" | "SET_BEAM" | "LOCK" | "UNLOCK" | "OPEN" | "CLOSE" | "SET_POSITION" | null,
  "value": number | string | null,
  "speech_response": string
}}

Aturan:
1. Kontrol sistem mobil → iot_action
2. Scene (mode parkir, mode perjalanan) → scene_action
3. Utamakan keselamatan.
4. speech_response selalu diisi.
5. Hanya JSON.

Daftar sistem mobil:
{devices_list}

Scene & group:
{scenes_list}
"""


class AIBrain:
    """LLM decision maker with devices + scenes + groups."""

    def __init__(
        self,
        device_manager: Optional[DeviceManager] = None,
        scene_manager: Optional[SceneManager] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.llm_api_key
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.llm_model
        self.device_manager = device_manager or DeviceManager()
        self.scene_manager = scene_manager or SceneManager(self.device_manager)

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _build_system_prompt(self) -> str:
        devices_str = self.device_manager.list_for_llm()
        scenes_str = self.scene_manager.list_for_llm()
        if self.device_manager.profile == "vehicle":
            return SYSTEM_PROMPT_VEHICLE.format(
                devices_list=devices_str, scenes_list=scenes_str
            )
        return SYSTEM_PROMPT_HOME.format(
            devices_list=devices_str, scenes_list=scenes_str
        )

    def think(self, user_text: str) -> Dict[str, Any]:
        if not user_text.strip():
            return {
                "type": "conversational",
                "device_id": None,
                "scene_id": None,
                "group_id": None,
                "command": None,
                "value": None,
                "speech_response": "Maaf, saya tidak mendengar apa-apa. Bisa diulangi?",
            }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.25,
                max_tokens=400,
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)

            for key in (
                "type",
                "device_id",
                "scene_id",
                "group_id",
                "command",
                "value",
                "speech_response",
            ):
                data.setdefault(key, None if key != "speech_response" else "Oke.")

            if data["type"] is None:
                data["type"] = "conversational"

            logger.info(f"AIBrain decision → {data}")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {
                "type": "conversational",
                "device_id": None,
                "scene_id": None,
                "group_id": None,
                "command": None,
                "value": None,
                "speech_response": "Maaf, terjadi sedikit gangguan. Coba lagi ya.",
            }
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return {
                "type": "conversational",
                "device_id": None,
                "scene_id": None,
                "group_id": None,
                "command": None,
                "value": None,
                "speech_response": "Maaf, saya sedang mengalami masalah koneksi.",
            }
