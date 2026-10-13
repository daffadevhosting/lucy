# Lucy — Smart Voice Assistant IoT

**Lucy** is an edge-first Smart Voice Assistant (Alexa / Google Home style) built for **Raspberry Pi** + **ESP32**.

## Features

- Porcupine offline wake word ("Hey Lucy")
- Whisper STT (API or local whisper.cpp)
- LLM brain (Grok / OpenAI) with structured JSON
- MQTT multi-room / multi-ESP32 discovery
- Vehicle (EV) profile
- Home Assistant MQTT discovery
- Scenes & group commands (mode malam, matikan semua lampu)

## Quick Start

```bash
git clone https://github.com/daffadevhosting/lucy.git
cd lucy
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # isi API keys
python run.py
```

## Docs

- [Custom Wake Word](docs/CUSTOM_WAKE_WORD.md)
- [Local Whisper.cpp](docs/LOCAL_WHISPER.md)
- [Multi-room & EV](docs/MULTI_ROOM_AND_EV.md)
- [Home Assistant & Scenes](docs/HOME_ASSISTANT_AND_SCENES.md)

## License

MIT
