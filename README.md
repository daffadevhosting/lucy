# Lucy — Edge-first Smart Voice Assistant for Raspberry Pi + ESP32

Lucy is an edge-first Smart Voice Assistant inspired by Alexa and Google Home, designed to run on Raspberry Pi and ESP32 devices with local-first voice processing, MQTT integration, and smart-home automation.

## Highlights

- Offline wake word detection with Porcupine
- Speech-to-text with Whisper (API or local whisper.cpp)
- LLM-powered assistant brain with structured JSON responses
- MQTT-based multi-room and multi-device discovery
- Home Assistant MQTT discovery support
- Scene and group control for smart home automation
- EV / vehicle profile support
- ESP32 firmware examples for node and legacy board setups

## What's New in This Release

This release adds the core voice assistant and home automation architecture for Lucy, including:

- Multi-room smart assistant support
- Home Assistant discovery and scene automation
- EV / vehicle-specific behavior support
- ESP32 firmware sketches for device nodes
- Documentation for setup, automation, and hardware integration
- Core Python modules for STT, assistant logic, MQTT control, and device management

## Architecture

Lucy is designed around a simple edge-first architecture:

- Raspberry Pi: runs the assistant brain, LLM integration, STT pipeline, and automation logic
- ESP32: acts as a local node for sensors, devices, and physical interactions
- MQTT: provides communication between Pi and ESP32 nodes
- Home Assistant: optional integration for discovery and smart-home automation

## Quick Start

### 1) Clone the repository

```bash
git clone https://github.com/daffadevhosting/lucy.git
cd lucy
```

### 2) Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3) Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4) Configure environment variables

Copy the example environment file and fill in the required keys:

```bash
cp .env.example .env
```

Then edit `.env` and set your:
- OpenAI / Grok / LLM API key
- MQTT broker settings
- Wi-Fi settings for ESP32
- Additional service credentials needed by your setup

### 5) Run Lucy

```bash
python run.py
```

## ESP32 Firmware

This repository includes ESP32 firmware examples for device nodes:

- `firmware/esp32/lucy_node.ino`
- `firmware/esp32/lucy_vehicle_node.ino`
- `firmware/esp32/lucy_esp32.ino`

Open the `.ino` files in the Arduino IDE or PlatformIO, configure your Wi-Fi and MQTT settings, then upload them to your ESP32 boards.

## Supported Features

- Wake word detection
- Offline voice command handling
- LLM response generation
- MQTT discovery for multi-room devices
- Smart home scenes
- Vehicle assistant profiles
- Home Assistant automation integration

## Documentation

- [Custom Wake Word](docs/CUSTOM_WAKE_WORD.md)
- [Local Whisper.cpp](docs/LOCAL_WHISPER.md)
- [Multi-room & EV](docs/MULTI_ROOM_AND_EV.md)
- [Home Assistant & Scenes](docs/HOME_ASSISTANT_AND_SCENES.md)

## Project Structure

```text
lucy/
├── docs/
├── firmware/
├── src/
├── .env.example
├── requirements.txt
├── run.py
├── README.md
├── LICENSE
└── .gitignore
```

## License

MIT
