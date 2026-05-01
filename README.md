# 🎬 Manga Recapper Pro - Temporal Sync Edition

> **The problem Gemini/Claude couldn't solve:** Scene-audio synchronization.
> **Our solution:** Per-scene narration generation with temporal constraints.

## 🚀 What This Fixes (vs. Your Old Pipeline)

| Issue | Old (Gemini) | New (This) |
|-------|-------------|------------|
| **Scene Sync** | One long narration dumped on whole video | Per-scene scripts matched to scene duration |
| **TTS Quality** | Edge TTS (robotic) | Kokoro TTS (natural, emotional) |
| **Script Length** | Random length, often too short | Word count calculated from scene duration |
| **Scene Detection** | None (random frames) | PySceneDetect + visual complexity analysis |
| **Action Filtering** | None | Auto-detects "badass" scenes via edge density |
| **Multi-format** | Manual | Auto: YouTube, Shorts, Instagram, TikTok |
| **API Limits** | N/A | No daily limits, iterate freely |

## 📁 Architecture

```
manga_recapper/
├── src/
│   ├── __init__.py              # Package init
│   ├── main_pipeline.py         # Orchestrator
│   ├── scene_detector.py        # Shot detection + complexity scoring
│   ├── audio_processor.py       # Whisper transcription + energy analysis
│   ├── script_generator.py      # Per-scene AI narration (the magic)
│   ├── tts_engine.py           # Kokoro TTS + fallback
│   └── video_assembler.py       # Scene-synced assembly + multi-format
├── .github/workflows/
│   └── main.yml                 # GitHub Actions CI/CD
├── requirements.txt             # Dependencies
├── setup_kokoro.sh             # Voice model setup
└── README.md                    # This file
```

## 🔧 Installation

### Local Setup

```bash
# 1. Clone/download this project
cd manga_recapper

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y ffmpeg espeak-ng

# 4. Setup Kokoro voice models
bash setup_kokoro.sh

# 5. Set your OpenRouter API key
export OPENROUTER_KEY="your_key_here"
```

### GitHub Actions (Recommended for heavy processing)

1. Fork this repo
2. Add `OPENROUTER_KEY` to Settings → Secrets
3. Add `cookies.txt` to repo root (for YouTube)
4. Add `bgm.mp3` to repo root (optional background music)
5. Run workflow manually with YouTube URL

## 🎬 Usage

### Command Line

```bash
cd src

# Basic: YouTube format only
python main_pipeline.py "https://youtube.com/watch?v=..."

# Multi-format output
python main_pipeline.py "https://youtube.com/watch?v=..."   --formats youtube youtube_shorts instagram tiktok

# With explicit API key
python main_pipeline.py "URL" --api-key "sk-or-v1-..."
```

### GitHub Actions

1. Go to Actions tab
2. Select "Manga Recapper Pro"
3. Click "Run workflow"
4. Paste YouTube URL
5. Select output formats
6. Download artifacts after completion

## 🧠 How Temporal Sync Works

This is the core innovation that fixes your "jump" issue:

1. **Scene Detection**: Video is split into actual shot boundaries (not random frames)
2. **Duration Calculation**: Each scene's length is measured precisely
3. **Word Budget**: AI is told exactly how many words fit in that duration
   - Formula: `words = duration_seconds × 2.2` (dramatic pacing)
4. **Per-Scene Generation**: Each scene gets its own narration script
5. **TTS Timing**: Kokoro generates audio per scene
6. **Assembly**: Scene N video + Scene N audio = perfectly synced segment
7. **Concatenate**: All synced segments joined in order

**Result:** Narration never jumps ahead or lags. It's physically impossible because the audio duration is constrained by the video segment duration.

## 🎯 Scene Selection ("Badass" Filter)

The pipeline auto-detects action scenes using:
- **Edge density**: More edges = more action/movement
- **Color variance**: High variance = visual intensity
- **Audio energy**: Loud moments = intense scenes

Scenes scoring >0.6 complexity are flagged as "action" and get more dramatic narration.

## 🎙️ Voice Options

Kokoro voices available after running `setup_kokoro.sh`:
- `af_bella` (default) - Young female, energetic
- `af_nicole` - Young female, calm
- `af_sarah` - Mature female, authoritative
- `am_adam` - Young male
- `am_michael` - Mature male, deep

Edit `tts_engine.py` to change the voice.

## 🛠️ Troubleshooting

### "No scenes detected"
- Lower threshold in `scene_detector.py` (default: 30.0)
- Check video has actual scene changes (not a static image)

### "TTS sounds robotic"
- Kokoro models didn't download. Run `bash setup_kokoro.sh`
- Or GPU not available - Kokoro works on CPU but slower

### "Script too short/long"
- The word count constraints auto-adjust, but you can tweak:
  - In `script_generator.py`: Change `2.2` to `2.5` for faster pace
  - Or `1.8` for slower, more dramatic pace

### "FFmpeg errors"
- Check watermark coordinates match your video resolution
- Default is 1280x720. For 1080p videos, scale coordinates up

### "YouTube download failed"
- Update `cookies.txt` (export from browser after logging into YouTube)
- Or try different format: `'format': 'best'` instead of height limit

## ⚠️ Legal Notice

This tool is for **educational/fair-use purposes only**:
- You must own rights to the source content, OR
- Use content under Creative Commons, OR
- Ensure your output qualifies as transformative fair use
- Do not use to circumvent content protection or redistribute copyrighted material

## 🔥 Why This Beats Gemini/Claude for Your Use Case

| Factor | Gemini | Claude | This Pipeline |
|--------|--------|--------|---------------|
| Scene sync | ❌ Failed | ❌ No built-in | ✅ Core feature |
| TTS quality | ❌ Edge TTS | ❌ No TTS | ✅ Kokoro |
| Iteration speed | ⚠️ Throttles | ❌ Daily limit | ✅ Unlimited |
| Context for big projects | ⚠️ Loses track | ✅ Good | ✅ Modular files |
| Debugging | ❌ Opaque | ✅ Good | ✅ Per-module logs |
| Multi-format | ❌ Manual | ❌ Manual | ✅ Auto |

## 📞 Next Steps

1. **Test with a short video first** (2-3 min manga recap)
2. **Check `workspace/scenes.json`** after run to verify scene detection
3. **Check `workspace/scripts.json`** to see per-scene narration
4. **Tweak watermark coordinates** in `main_pipeline.py` for your source
5. **Add your BGM** file as `bgm.mp3` in repo root

---

**Built to fix exactly what Gemini and Claude couldn't solve.**
