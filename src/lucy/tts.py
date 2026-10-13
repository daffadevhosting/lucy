"""Text-to-Speech player — supports Piper (offline), ElevenLabs, and espeak fallback."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from loguru import logger

from .config import settings


class TTSPlayer:
    """Unified TTS interface."""

    def __init__(self, engine: Optional[str] = None) -> None:
        self.engine = (engine or settings.tts_engine).lower()
        self._piper_voice = None
        self._elevenlabs = None

        if self.engine == "piper":
            self._init_piper()
        elif self.engine == "elevenlabs":
            self._init_elevenlabs()
        else:
            logger.info("TTS engine set to espeak (fallback)")

    def _init_piper(self) -> None:
        model = Path(settings.piper_model_path)
        if not model.exists():
            logger.warning(
                f"Piper model not found at {model}. "
                "Falling back to espeak. Download Indonesian model from "
                "https://github.com/rhasspy/piper/releases"
            )
            self.engine = "espeak"
            return
        try:
            from piper import PiperVoice  # type: ignore

            self._piper_voice = PiperVoice.load(str(model))
            logger.success(f"Piper TTS loaded: {model.name}")
        except Exception as e:
            logger.warning(f"Failed to load Piper: {e}. Using espeak.")
            self.engine = "espeak"

    def _init_elevenlabs(self) -> None:
        if not settings.elevenlabs_api_key:
            logger.warning("ELEVENLABS_API_KEY missing. Falling back to espeak.")
            self.engine = "espeak"
            return
        try:
            from elevenlabs.client import ElevenLabs

            self._elevenlabs = ElevenLabs(api_key=settings.elevenlabs_api_key)
            logger.success("ElevenLabs TTS ready")
        except Exception as e:
            logger.warning(f"ElevenLabs init failed: {e}. Using espeak.")
            self.engine = "espeak"

    def speak(self, text: str) -> None:
        """Convert text to speech and play it."""
        if not text or not text.strip():
            return

        logger.info(f"TTS ({self.engine}) → «{text}»")

        try:
            if self.engine == "piper" and self._piper_voice:
                self._speak_piper(text)
            elif self.engine == "elevenlabs" and self._elevenlabs:
                self._speak_elevenlabs(text)
            else:
                self._speak_espeak(text)
        except Exception as e:
            logger.error(f"TTS playback error: {e}")
            self._speak_espeak(text)

    def _speak_piper(self, text: str) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with open(tmp_path, "wb") as f:
                self._piper_voice.synthesize(text, f)
            subprocess.run(["aplay", "-q", tmp_path], check=False)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _speak_elevenlabs(self, text: str) -> None:
        from elevenlabs import play

        audio = self._elevenlabs.generate(
            text=text,
            voice=settings.elevenlabs_voice_id,
            model="eleven_multilingual_v2",
        )
        play(audio)

    def _speak_espeak(self, text: str) -> None:
        """Fallback using espeak (available on most Raspberry Pi OS)."""
        safe = text.replace('"', '\\"')
        subprocess.run(
            ["espeak", "-v", "id", "-s", "150", safe],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
