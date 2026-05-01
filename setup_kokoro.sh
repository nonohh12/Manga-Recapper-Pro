#!/bin/bash
# setup_kokoro.sh
# Downloads Kokoro voice models for local TTS

echo "🔧 Setting up Kokoro TTS..."

# Create models directory
mkdir -p models/kokoro

# Download Kokoro ONNX models
echo "📥 Downloading voice models..."

# Primary voices
VOICES=("af_bella" "af_nicole" "af_sarah" "am_adam" "am_michael")

for voice in "${VOICES[@]}"; do
    echo "  → Downloading $voice..."
    curl -L -o "models/kokoro/${voice}.onnx"         "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/${voice}.onnx"         2>/dev/null || echo "    ⚠️  Failed to download $voice"
done

echo "✅ Kokoro setup complete!"
echo "Available voices: ${VOICES[*]}"
