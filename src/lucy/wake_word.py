"""Wake Word detection using Picovoice Porcupine."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pvporcupine
import sounddevice as sd
from loguru import logger

from .config import settings


class WakeWordDetector:
    """Offline low-latency wake word engine.

    Supports:
    - Custom .ppn model (recommended for "Hey Lucy")
    - Built-in keywords (porcupine, jarvis, computer, etc.) as fallback
    """

    def __init__(
        self,
        access_key: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        keyword_paths: Optional[List[str]] = None,
        sensitivities: Optional[List[float]] = None,
    ) -> None:
        self.access_key = access_key or settings.porcupine_access_key

        if keyword_paths is not None:
            self.keyword_paths = keyword_paths
            self.keywords = None
        elif settings.porcupine_keyword_path:
            path = Path(settings.porcupine_keyword_path)
            if not path.is_absolute():
                from .config import ROOT_DIR
                path = ROOT_DIR / path
            self.keyword_paths = [str(path)]
            self.keywords = None
        else:
            self.keyword_paths = None
            self.keywords = keywords or [settings.porcupine_keyword]

        sens = settings.porcupine_sensitivity
        if sensitivities is not None:
            self.sensitivities = sensitivities
        elif self.keyword_paths:
            self.sensitivities = [sens] * len(self.keyword_paths)
        else:
            self.sensitivities = [sens] * len(self.keywords or ["porcupine"])

        self.porcupine: Optional[pvporcupine.Porcupine] = None
        self._running = False

    def start(self) -> None:
        """Initialize Porcupine engine."""
        if not self.access_key:
            raise ValueError("Porcupine access key is required (PORCUPINE_ACCESS_KEY)")

        kwargs = {
            "access_key": self.access_key,
            "sensitivities": self.sensitivities,
        }

        if self.keyword_paths:
            for p in self.keyword_paths:
                if not Path(p).exists():
                    raise FileNotFoundError(
                        f"Custom wake word model not found: {p}\n"
                        "Train 'Hey Lucy' at https://console.picovoice.ai/ "
                        "and place the .ppn file under models/wakewords/"
                    )
            kwargs["keyword_paths"] = self.keyword_paths
            label = self.keyword_paths
        else:
            kwargs["keywords"] = self.keywords
            label = self.keywords

        self.porcupine = pvporcupine.create(**kwargs)
        logger.info(
            f"WakeWord ready | model={label} | sensitivity={self.sensitivities} "
            f"| frame_length={self.porcupine.frame_length}"
        )

    def listen(self) -> bool:
        """Blocking listen loop. Returns True when wake word is detected."""
        if not self.porcupine:
            raise RuntimeError("Call start() before listen()")

        frame_length = self.porcupine.frame_length
        self._running = True

        logger.info('Listening for wake word "Hey Lucy"...')

        with sd.InputStream(
            samplerate=settings.sample_rate,
            channels=settings.channels,
            dtype="int16",
            blocksize=frame_length,
        ) as stream:
            while self._running:
                pcm, overflowed = stream.read(frame_length)
                if overflowed:
                    logger.warning("Audio buffer overflow")
                pcm = pcm.flatten()
                result = self.porcupine.process(pcm)
                if result >= 0:
                    logger.success(f"Wake word detected (index={result})")
                    return True
        return False

    def stop(self) -> None:
        self._running = False

    def cleanup(self) -> None:
        """Release resources."""
        self.stop()
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None
            logger.debug("Porcupine cleaned up")
