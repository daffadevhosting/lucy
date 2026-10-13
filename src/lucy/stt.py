"""Speech-to-Text client.

Supports three engines (selected via STT_ENGINE):
  - api            → OpenAI Whisper API (default, easiest)
  - whispercpp     → Local whisper.cpp via pywhispercpp (recommended offline)
  - faster-whisper → Local faster-whisper (CTranslate2)
"""

from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger

from .config import ROOT_DIR, settings


class STTClient:
    """Unified STT interface with pluggable backends."""

    def __init__(self, engine: Optional[str] = None, language: Optional[str] = None) -> None:
        self.engine = (engine or settings.stt_engine).lower()
        self.language = language or settings.stt_language
        self._backend = None

        if self.engine == "api":
            self._init_api()
        elif self.engine in ("whispercpp", "whisper.cpp", "local"):
            self.engine = "whispercpp"
            self._init_whispercpp()
        elif self.engine in ("faster-whisper", "faster_whisper"):
            self.engine = "faster-whisper"
            self._init_faster_whisper()
        else:
            raise ValueError(
                f"Unknown STT_ENGINE={self.engine}. Use: api | whispercpp | faster-whisper"
            )

        logger.info(f"STT engine ready → {self.engine}")

    def _init_api(self) -> None:
        from openai import OpenAI
        self._client = OpenAI(api_key=settings.stt_api_key, base_url=settings.stt_base_url)
        self._model = settings.stt_model

    def _resolve_model_path(self) -> Path:
        path = Path(settings.stt_local_model)
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path

    def _init_whispercpp(self) -> None:
        try:
            from pywhispercpp.model import Model
        except ImportError as e:
            raise ImportError(
                "pywhispercpp is required for local Whisper.cpp.\n"
                "Install with: pip install git+https://github.com/absadiki/pywhispercpp"
            ) from e

        model_path = self._resolve_model_path()
        if not model_path.exists():
            raise FileNotFoundError(
                f"Local Whisper model not found: {model_path}\n"
                "Download with: ./scripts/download_whisper_models.sh tiny"
            )

        self._backend = Model(
            str(model_path),
            n_threads=settings.stt_n_threads,
            print_realtime=False,
            print_progress=False,
        )
        logger.success(
            f"whisper.cpp loaded | model={model_path.name} | threads={settings.stt_n_threads}"
        )

    def _init_faster_whisper(self) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise ImportError(
                "faster-whisper is required.\nInstall with: pip install faster-whisper"
            ) from e

        model_path = self._resolve_model_path()
        model_arg = str(model_path) if model_path.exists() else settings.stt_local_model
        self._backend = WhisperModel(
            model_arg, device="cpu", compute_type="int8", cpu_threads=settings.stt_n_threads
        )
        logger.success(f"faster-whisper loaded | model={model_arg} | threads={settings.stt_n_threads}")

    def transcribe(self, audio_np: np.ndarray, sample_rate: int | None = None) -> str:
        """Convert int16 numpy audio → text."""
        sr = sample_rate or settings.sample_rate
        if self.engine == "api":
            return self._transcribe_api(audio_np, sr)
        if self.engine == "whispercpp":
            return self._transcribe_whispercpp(audio_np, sr)
        if self.engine == "faster-whisper":
            return self._transcribe_faster_whisper(audio_np, sr)
        return ""

    def _transcribe_api(self, audio_np: np.ndarray, sr: int) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(audio_np.tobytes())
        try:
            with open(tmp_path, "rb") as f:
                result = self._client.audio.transcriptions.create(
                    model=self._model, file=f, language=self.language, response_format="text"
                )
            text = result.strip() if isinstance(result, str) else str(result).strip()
            logger.success(f"STT (api) → «{text}»")
            return text
        except Exception as e:
            logger.error(f"STT API failed: {e}")
            return ""
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _transcribe_whispercpp(self, audio_np: np.ndarray, sr: int) -> str:
        try:
            audio_f32 = audio_np.astype(np.float32) / 32768.0
            segments = self._backend.transcribe(
                audio_f32, language=self.language if self.language != "auto" else None
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            logger.success(f"STT (whisper.cpp) → «{text}»")
            return text
        except Exception as e:
            logger.error(f"STT whisper.cpp failed: {e}")
            return ""

    def _transcribe_faster_whisper(self, audio_np: np.ndarray, sr: int) -> str:
        try:
            audio_f32 = audio_np.astype(np.float32) / 32768.0
            segments, _info = self._backend.transcribe(
                audio_f32,
                language=self.language if self.language != "auto" else None,
                beam_size=1,
                vad_filter=True,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            logger.success(f"STT (faster-whisper) → «{text}»")
            return text
        except Exception as e:
            logger.error(f"STT faster-whisper failed: {e}")
            return ""
