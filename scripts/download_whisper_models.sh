#!/bin/bash
# Download ggml Whisper models for local whisper.cpp / pywhispercpp
# Usage:
#   ./scripts/download_whisper_models.sh tiny
#   ./scripts/download_whisper_models.sh base
#   ./scripts/download_whisper_models.sh small
#
# Models are saved to models/whisper/

set -e

MODEL_SIZE="${1:-tiny}"
MODELS_DIR="$(cd "$(dirname "$0")/.." && pwd)/models/whisper"
BASE_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main"

mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

case "$MODEL_SIZE" in
  tiny|tiny.en|base|base.en|small|small.en|medium|medium.en)
    FILE="ggml-${MODEL_SIZE}.bin"
    ;;
  tiny-q5_0|base-q5_0|small-q5_0)
    FILE="ggml-${MODEL_SIZE}.bin"
    ;;
  *)
    echo "Supported: tiny, tiny.en, base, base.en, small, small.en, medium, ..."
    echo "Quantized: tiny-q5_0, base-q5_0, small-q5_0"
    exit 1
    ;;
esac

if [[ -f "$FILE" ]]; then
  echo "Already exists: $MODELS_DIR/$FILE"
  exit 0
fi

echo "Downloading $FILE ..."
echo "Target: $MODELS_DIR/$FILE"
curl -L --progress-bar -o "$FILE" "${BASE_URL}/${FILE}"

echo ""
echo "Done → $MODELS_DIR/$FILE"
echo ""
echo "Set in .env:"
echo "  STT_ENGINE=whispercpp"
echo "  STT_LOCAL_MODEL=models/whisper/$FILE"
echo "  STT_N_THREADS=4"
