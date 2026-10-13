"""Configuration loader for Lucy."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
DEVICES_PATH = ROOT_DIR / "config" / "devices.yaml"


def load_env() -> None:
    """Load .env file if present."""
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
        logger.debug(f"Loaded environment from {ENV_PATH}")
    else:
        logger.warning(f".env not found at {ENV_PATH}. Using system environment.")


class Settings:
    """Central configuration object."""

    def __init__(self) -> None:
        load_env()

        self.porcupine_access_key: str = os.getenv("PORCUPINE_ACCESS_KEY", "")
        self.porcupine_keyword_path: Optional[str] = os.getenv("PORCUPINE_KEYWORD_PATH") or None
        self.porcupine_keyword: str = os.getenv("PORCUPINE_KEYWORD", "porcupine")
        self.porcupine_sensitivity: float = float(os.getenv("PORCUPINE_SENSITIVITY", "0.65"))

        self.llm_api_key: str = os.getenv("LLM_API_KEY", "")
        self.llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.x.ai/v1")
        self.llm_model: str = os.getenv("LLM_MODEL", "grok-2-latest")

        self.stt_engine: str = os.getenv("STT_ENGINE", "api").lower()
        self.stt_api_key: str = os.getenv("STT_API_KEY", self.llm_api_key)
        self.stt_base_url: str = os.getenv("STT_BASE_URL", "https://api.openai.com/v1")
        self.stt_model: str = os.getenv("STT_MODEL", "whisper-1")
        self.stt_language: str = os.getenv("STT_LANGUAGE", "id")
        self.stt_local_model: str = os.getenv(
            "STT_LOCAL_MODEL", "models/whisper/ggml-tiny.bin"
        )
        self.stt_n_threads: int = int(os.getenv("STT_N_THREADS", "4"))
        self.stt_translate: bool = os.getenv("STT_TRANSLATE", "false").lower() == "true"

        self.mqtt_broker: str = os.getenv("MQTT_BROKER", "localhost")
        self.mqtt_port: int = int(os.getenv("MQTT_PORT", "1883"))
        self.mqtt_username: Optional[str] = os.getenv("MQTT_USERNAME") or None
        self.mqtt_password: Optional[str] = os.getenv("MQTT_PASSWORD") or None
        self.mqtt_client_id: str = os.getenv("MQTT_CLIENT_ID", "lucy-edge-01")

        self.tts_engine: str = os.getenv("TTS_ENGINE", "piper").lower()
        self.piper_model_path: str = os.getenv(
            "PIPER_MODEL_PATH", str(ROOT_DIR / "models" / "id_ID-media-medium.onnx")
        )
        self.piper_config_path: str = os.getenv(
            "PIPER_CONFIG_PATH", str(ROOT_DIR / "models" / "id_ID-media-medium.onnx.json")
        )
        self.elevenlabs_api_key: Optional[str] = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_voice_id: str = os.getenv(
            "ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"
        )

        self.sample_rate: int = int(os.getenv("SAMPLE_RATE", "16000"))
        self.record_seconds: float = float(os.getenv("RECORD_SECONDS", "4.5"))
        self.channels: int = int(os.getenv("CHANNELS", "1"))

        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.log_file: str = os.getenv("LOG_FILE", str(ROOT_DIR / "logs" / "lucy.log"))

        self.devices: Dict[str, Any] = self._load_devices()

    def _load_devices(self) -> Dict[str, Any]:
        if not DEVICES_PATH.exists():
            logger.warning(f"devices.yaml not found at {DEVICES_PATH}")
            return {}
        with open(DEVICES_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("devices", {})

    def validate(self) -> None:
        """Raise if critical settings are missing."""
        missing = []
        if not self.porcupine_access_key:
            missing.append("PORCUPINE_ACCESS_KEY")
        if not self.llm_api_key:
            missing.append("LLM_API_KEY")
        if self.stt_engine == "api" and not self.stt_api_key:
            missing.append("STT_API_KEY (or LLM_API_KEY)")
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill the values."
            )


settings = Settings()
