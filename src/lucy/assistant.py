"""Main Lucy orchestrator — ties all modules together."""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger
from rich.console import Console
from rich.panel import Panel

from .audio_recorder import AudioRecorder
from .brain import AIBrain
from .config import settings
from .device_manager import DeviceManager
from .mqtt_controller import MQTTController
from .scene_manager import SceneManager
from .stt import STTClient
from .tts import TTSPlayer
from .wake_word import WakeWordDetector

console = Console()


def setup_logging() -> None:
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    )
    logger.add(log_path, level="DEBUG", rotation="10 MB", retention="7 days", encoding="utf-8")


class Lucy:
    """Smart Voice Assistant IoT — Lucy (Home + Vehicle + Scenes + HA)."""

    def __init__(self) -> None:
        setup_logging()
        settings.validate()

        self.device_manager = DeviceManager()
        self.scene_manager = SceneManager(self.device_manager)
        self.wake = WakeWordDetector()
        self.recorder = AudioRecorder()
        self.stt = STTClient()
        self.brain = AIBrain(
            device_manager=self.device_manager,
            scene_manager=self.scene_manager,
        )
        self.mqtt = MQTTController(device_manager=self.device_manager)
        self.tts = TTSPlayer()

        self._running = False
        self.enable_ha = os.getenv("HA_DISCOVERY", "true").lower() in ("1", "true", "yes")

    def _print_banner(self) -> None:
        profile = self.device_manager.profile
        subtitle = "Vehicle EV Mode" if profile == "vehicle" else "Home Multi-room Mode"
        banner = """
 ██╗     ██╗   ██╗ ██████╗██╗   ██╗
 ██║     ██║   ██║██╔════╝╚██╗ ██╔╝
 ██║     ██║   ██║██║      ╚████╔╝ 
 ██║     ██║   ██║██║       ╚██╔╝  
 ███████╗╚██████╔╝╚██████╗   ██║   
 ╚══════╝ ╚═════╝  ╚═════╝   ╚═╝   
        Smart Voice Assistant IoT
        """
        console.print(Panel(banner, style="bold magenta", title="Lucy v1.2", subtitle=subtitle))
        n = len(self.device_manager.devices)
        s = len(self.scene_manager.scenes)
        console.print(
            f"  Profile: [cyan]{profile}[/] | Devices: [green]{n}[/] | "
            f"Scenes: [green]{s}[/] | HA Discovery: [yellow]{self.enable_ha}[/]\n"
        )

    def start(self) -> None:
        self._print_banner()
        logger.info("Starting Lucy...")
        self.wake.start()
        self.mqtt.connect()
        self.mqtt.request_discovery()
        if self.enable_ha:
            try:
                self.mqtt.publish_ha_discovery()
            except Exception as e:
                logger.warning(f"HA discovery failed: {e}")
        self._running = True
        logger.success("Lucy is ready. Say the wake word...")

    def _execute_actions(self, actions: List[Dict[str, Any]]) -> int:
        count = 0
        for act in actions:
            did = act.get("device_id")
            cmd = act.get("command")
            val = act.get("value")
            if not did or not cmd:
                continue
            if not self.device_manager.get(did):
                logger.warning(f"Skip unknown device in scene/group: {did}")
                continue
            self.mqtt.publish_action(did, cmd, val)
            count += 1
        return count

    def _handle_decision(self, decision: Dict[str, Any]) -> None:
        dtype = decision.get("type")

        if dtype == "iot_action":
            device_id = decision.get("device_id")
            command = decision.get("command")
            value = decision.get("value")
            if device_id and command:
                dev = self.device_manager.get(device_id)
                if not dev:
                    self.tts.speak(f"Maaf, perangkat {device_id} belum terdaftar.")
                    return
                if not self.device_manager.validate_action(device_id, command):
                    self.tts.speak(f"Perintah {command} tidak didukung untuk {dev.name}.")
                    return
                self.mqtt.publish_action(device_id, command, value)
            return

        if dtype == "scene_action":
            scene_id = decision.get("scene_id")
            actions = self.scene_manager.resolve("scene_action", scene_id=scene_id)
            if not actions:
                self.tts.speak("Scene tidak ditemukan.")
                return
            n = self._execute_actions(actions)
            logger.success(f"Scene '{scene_id}' → {n} actions")
            return

        if dtype == "group_action":
            group_id = decision.get("group_id")
            command = decision.get("command")
            value = decision.get("value")
            actions = self.scene_manager.resolve(
                "group_action", group_id=group_id, command=command, value=value
            )
            if not actions:
                self.tts.speak("Tidak ada perangkat yang cocok di group itu.")
                return
            n = self._execute_actions(actions)
            logger.success(f"Group '{group_id}' {command} → {n} devices")
            return

    def run_forever(self) -> None:
        self.start()

        def _signal_handler(sig, frame):
            logger.info("Shutdown signal received")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        try:
            while self._running:
                self.device_manager.check_timeouts()
                if not self.wake.listen():
                    continue
                audio = self.recorder.record()
                text = self.stt.transcribe(audio)
                if not text:
                    self.tts.speak("Maaf, saya tidak mendengar dengan jelas.")
                    continue
                decision = self.brain.think(text)
                self._handle_decision(decision)
                speech = decision.get("speech_response", "Baik.")
                self.tts.speak(speech)
        except Exception as e:
            logger.exception(f"Fatal error in main loop: {e}")
            self.tts.speak("Maaf, terjadi kesalahan sistem.")
        finally:
            self.stop()

    def stop(self) -> None:
        self._running = False
        self.wake.cleanup()
        self.mqtt.disconnect()
        logger.info("Lucy stopped.")
