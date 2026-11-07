#!/bin/bash
# One-time setup for the Qwen narrator voice (tts "qwen"). CPU build of torch, no GPU needed.
# Takes a few minutes in a fresh container; the 1.7B model (about 4 GB) downloads on first render.
set -e
python3 -c "import torch, qwen_tts" 2>/dev/null && { echo "qwen voice already installed"; exit 0; }
python3 -m pip install -q torch torchaudio --index-url https://download.pytorch.org/whl/cpu
python3 -m pip install -q "qwen-tts>=0.1.1" soundfile
echo "qwen voice installed"
