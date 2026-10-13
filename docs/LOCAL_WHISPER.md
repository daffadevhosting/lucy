# Local Whisper.cpp Integration

Lucy mendukung **Speech-to-Text offline** menggunakan whisper.cpp (via `pywhispercpp`) atau `faster-whisper`.

---

## Rekomendasi Model di Raspberry Pi

| Model | Ukuran | Kecepatan (Pi 5) | Rekomendasi |
|-------|--------|------------------|-------------|
| `tiny` | ~75 MB | Sangat cepat | **Voice command** |
| `base` | ~142 MB | ~ real-time | Sweet spot |
| `small` | ~466 MB | Lebih lambat | Akurasi tinggi |

## Install

```bash
pip install git+https://github.com/absadiki/pywhispercpp
./scripts/download_whisper_models.sh tiny
```

## Config `.env`

```env
STT_ENGINE=whispercpp
STT_LOCAL_MODEL=models/whisper/ggml-tiny.bin
STT_N_THREADS=4
STT_LANGUAGE=id
```

## Referensi

- [whisper.cpp](https://github.com/ggml-org/whisper.cpp)
- [pywhispercpp](https://github.com/absadiki/pywhispercpp)
