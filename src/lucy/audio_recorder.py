"""Audio recording module."""

from __future__ import annotations

import numpy as np
import sounddevice as sd
from loguru import logger

from .config import settings


class AudioRecorder:
    """Record audio from microphone after wake word."""

    def __init__(
        self,
        sample_rate: int | None = None,
        channels: int | None = None,
        duration: float | None = None,
    ) -> None:
        self.sample_rate = sample_rate or settings.sample_rate
        self.channels = channels or settings.channels
        self.duration = duration or settings.record_seconds

    def record(self, duration: float | None = None) -> np.ndarray:
        """
        Record mono audio and return as int16 numpy array.
        """
        dur = duration or self.duration
        logger.info(f"Recording {dur:.1f}s ...")

        audio = sd.rec(
            int(dur * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocking=True,
        )
        audio = audio.flatten()
        logger.success(f"Recorded {len(audio)} samples ({len(audio)/self.sample_rate:.2f}s)")
        return audio

    def record_until_silence(
        self,
        max_duration: float = 8.0,
        silence_threshold: int = 500,
        silence_duration: float = 1.2,
    ) -> np.ndarray:
        """
        Advanced: record until silence detected (VAD-like).
        Simple energy-based implementation.
        """
        logger.info("Recording until silence...")
        frames = []
        frame_len = int(0.1 * self.sample_rate)  # 100ms frames
        silent_frames = 0
        max_silent = int(silence_duration / 0.1)
        max_frames = int(max_duration / 0.1)

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=frame_len,
        ) as stream:
            for _ in range(max_frames):
                data, _ = stream.read(frame_len)
                data = data.flatten()
                frames.append(data)
                energy = np.abs(data).mean()
                if energy < silence_threshold:
                    silent_frames += 1
                    if silent_frames >= max_silent and len(frames) > 10:
                        break
                else:
                    silent_frames = 0

        audio = np.concatenate(frames)
        logger.success(f"Recorded until silence: {len(audio)/self.sample_rate:.2f}s")
        return audio
