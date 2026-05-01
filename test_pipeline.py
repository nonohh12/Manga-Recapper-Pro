#!/usr/bin/env python3
"""
test_pipeline.py
Quick test script to verify each module works independently.
Run this before the full pipeline to catch issues early.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test all imports."""
    print("🔍 Testing imports...")
    try:
        from scene_detector import SceneDetector
        from audio_processor import AudioProcessor
        from script_generator import ScriptGenerator
        from tts_engine import TTSEngine
        from video_assembler import VideoAssembler
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_ffmpeg():
    """Test FFmpeg installation."""
    import subprocess
    print("🔍 Testing FFmpeg...")
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.split('
')[0]
            print(f"✅ FFmpeg: {version}")
            return True
    except:
        pass
    print("❌ FFmpeg not found. Install: sudo apt-get install ffmpeg")
    return False

def test_yt_dlp():
    """Test yt-dlp."""
    print("🔍 Testing yt-dlp...")
    try:
        import yt_dlp
        print(f"✅ yt-dlp: {yt_dlp.version.__version__}")
        return True
    except Exception as e:
        print(f"❌ yt-dlp error: {e}")
        return False

def test_kokoro():
    """Test Kokoro TTS."""
    print("🔍 Testing Kokoro TTS...")
    try:
        from kokoro import KPipeline
        print("✅ Kokoro available")
        return True
    except ImportError:
        print("⚠️  Kokoro not installed. Will use fallback TTS.")
        print("   Install: pip install kokoro")
        return False

def test_whisper():
    """Test Whisper."""
    print("🔍 Testing Whisper...")
    try:
        import whisper
        print("✅ Whisper available")
        return True
    except ImportError:
        print("⚠️  Whisper not installed. Will skip transcription.")
        print("   Install: pip install openai-whisper")
        return False

def test_api_key():
    """Test API key."""
    import os
    print("🔍 Testing API key...")
    key = os.environ.get("OPENROUTER_KEY")
    if key:
        print(f"✅ API key found ({key[:10]}...)")
        return True
    print("❌ OPENROUTER_KEY not set")
    print("   Export: export OPENROUTER_KEY='your_key'")
    return False

def main():
    print("="*60)
    print("🧪 Manga Recapper - Pre-flight Check")
    print("="*60)

    tests = [
        ("Imports", test_imports),
        ("FFmpeg", test_ffmpeg),
        ("yt-dlp", test_yt_dlp),
        ("Kokoro TTS", test_kokoro),
        ("Whisper", test_whisper),
        ("API Key", test_api_key),
    ]

    results = {}
    for name, test_fn in tests:
        print(f"
--- {name} ---")
        results[name] = test_fn()

    print("
" + "="*60)
    print("📊 Results:")
    passed = sum(results.values())
    total = len(results)
    for name, ok in results.items():
        status = "✅" if ok else "❌"
        print(f"   {status} {name}")
    print(f"
{passed}/{total} checks passed")

    if passed < total:
        print("
⚠️  Fix failed checks before running full pipeline")
        return 1
    else:
        print("
🚀 Ready to run full pipeline!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
