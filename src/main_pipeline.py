"""
main_pipeline.py
Complete Manga Recapper Pipeline with temporal sync.
Merges Gemini's working download approach with Kokoro TTS and scene sync.
"""
import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
import argparse

# Import our modules
from scene_detector import SceneDetector, Scene
from audio_processor import AudioProcessor
from script_generator import ScriptGenerator, SceneScript
from tts_engine import TTSEngine, TTSSegment
from video_assembler import VideoAssembler, FORMATS

# --- CONFIGURATION ---
WORK_DIR = Path("workspace")
OUTPUT_DIR = Path("output")
COOKIE_FILE = "../cookies.txt"  # Relative to src/ directory
BGM_FILE = "bgm.mp3"

# Watermark regions (adjust based on your source videos)
DEFAULT_WATERMARKS = [
    {"x": 40, "y": 40, "w": 220, "h": 100},    # Top Left
    {"x": 900, "y": 30, "w": 350, "h": 150},   # Top Right
    {"x": 100, "y": 600, "w": 1080, "h": 100}  # Bottom Subtitles
]

class MangaRecapper:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.work_dir = WORK_DIR
        self.output_dir = OUTPUT_DIR

        os.makedirs(self.work_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def run(self, video_url: str, target_formats: List[str] = None):
        """Run the complete pipeline."""
        if target_formats is None:
            target_formats = ["youtube"]

        print("\n" + "="*60)
        print("🎬 MANGA RECAPPER PRO - Temporal Sync Edition")
        print("="*60 + "\n")

        try:
            # Step 1: Download
            video_path = self._download_video(video_url)
            if not video_path:
                print("❌ Download failed. Exiting.")
                return False

            # Step 2: Detect scenes
            print("\n🔍 STEP 1: Scene Detection")
            detector = SceneDetector(video_path, self.work_dir)
            scenes = detector.detect_scenes(threshold=30.0)
            detector.save_scene_data()

            print(f"✅ Scene detection complete. Found {len(scenes)} scenes")

            if not scenes:
                print("❌ No scenes detected. Exiting.")
                return False

            # Step 3: Transcribe audio
            print("\n🎙️ STEP 2: Audio Transcription")
            audio_proc = AudioProcessor(video_path, self.work_dir)
            audio_proc.extract_audio()
            transcript = audio_proc.transcribe()
            print(f"✅ Transcription complete. Found {len(transcript)} segments")
            audio_proc.save_transcript()

            # Step 4: Generate per-scene scripts
            print("\n📝 STEP 3: Script Generation (Per Scene)")
            script_gen = ScriptGenerator(self.api_key, self.work_dir)

            # Convert scenes to dicts
            scene_dicts = [
                {
                    "start": s.start_time,
                    "end": s.end_time,
                    "duration": s.duration,
                    "complexity": s.complexity_score,
                    "is_action": s.is_action_scene,
                    "frame_path": str(s.frame_path)
                }
                for s in scenes
            ]

            # Get video context from first few scenes
            video_context = self._get_video_context(scene_dicts[:3])

            scripts = script_gen.generate_per_scene(
                scenes=scene_dicts,
                transcript_segments=[
                    {"start": t.start, "end": t.end, "text": t.text, "energy": t.audio_energy}
                    for t in transcript
                ],
                video_context=video_context
            )
            print(f"✅ Script generation complete. Generated {len(scripts)} scene scripts")
            script_gen.save_scripts(scripts)

            # Step 5: Generate TTS
            print("\n🗣️ STEP 4: TTS Generation (Kokoro)")
            tts_engine = TTSEngine(self.work_dir, voice="af_bella")

            script_dicts = [
                {
                    "narration": s.narration,
                    "scene_start": s.scene_start,
                    "scene_end": s.scene_end,
                    "duration": s.duration
                }
                for s in scripts
            ]

            tts_segments = tts_engine.generate_segments(script_dicts, speed=1.0)

            print(f"✅ TTS generation complete. Generated {len(tts_segments)} audio segments")
            # Step 6: Assemble video
            print("\n🎬 STEP 5: Video Assembly")
            assembler = VideoAssembler(video_path, self.work_dir, self.output_dir)

            bgm_path = Path(BGM_FILE) if os.path.exists(BGM_FILE) else None

            results = assembler.generate_all_formats(
                scenes=scene_dicts,
                tts_segments=[
                    {
                        "output_path": str(s.output_path),
                        "scene_start": s.scene_start,
                        "scene_end": s.scene_end
                    }
                    for s in tts_segments
                ],
                watermark_regions=DEFAULT_WATERMARKS,
                bgm_path=bgm_path,
                output_name="manga_recap"
            )

            # Summary
            print("\n" + "="*60)
            print("✅ SUCCESS! Output files:")
            for fmt, path in results.items():
                if path.exists():
                    size = path.stat().st_size / (1024*1024)
                    print(f"   📁 {fmt}: {path} ({size:.1f} MB)")
            print("="*60)

            return True

        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _download_video(self, url: str) -> Optional[Path]:
        """Download video from YouTube (TESTING MODE: First 4 minutes only)."""
        print(f"📥 Downloading (TEST MODE - 4min limit): {url}")

        output_path = self.work_dir / "raw.mp4"

        # GEMINI'S WORKING CONFIGURATION - DO NOT CHANGE
        ydl_opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best',
            'outtmpl': str(output_path),
            'merge_output_format': 'mp4',
            'cookiefile': '../cookies.txt',  # Repo root from src/ directory
            'remote_components': ['ejs:github'],  # ← KEY: Downloads challenge solver
            'nocheckcertificate': True,
        }

        # TESTING MODE: Only download first 4 minutes (240 seconds)
        # Using simpler approach: download full then trim with FFmpeg
        # This avoids yt-dlp format conflicts with download_ranges

        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                print(f"✅ Downloaded: {title} (Original: {duration//60}min)")

                # Trim to 4 minutes using FFmpeg (more reliable than yt-dlp ranges)
                if duration > 240:
                    print("✂️  Trimming to first 4 minutes...")
                    trimmed_path = self.work_dir / "raw_trimmed.mp4"
                    cmd = [
                        "ffmpeg", "-y", "-i", str(output_path),
                        "-t", "240",  # First 240 seconds
                        "-c", "copy",  # Copy without re-encoding
                        str(trimmed_path)
                    ]
                    subprocess.run(cmd, capture_output=True, check=True)

                    # Replace original with trimmed
                    os.remove(output_path)
                    os.rename(trimmed_path, output_path)
                    print("✅ Trimmed to 4 minutes")

                print(f"✅ Download complete. File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
                return output_path

        except Exception as e:
            print(f"❌ Download error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_video_context(self, first_scenes: List[Dict]) -> str:
        """Get initial context about the video for better narration."""
        action_count = sum(1 for s in first_scenes if s.get("is_action", False))
        total = len(first_scenes)

        if action_count / total > 0.5:
            return "Intense action/battle manga with high-stakes fights"
        else:
            return "Story-driven manga with character development and plot twists"

def main():
    parser = argparse.ArgumentParser(description="Manga Recapper Pro")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--formats", nargs="+", default=["youtube"],
                       choices=["youtube", "youtube_shorts", "instagram", "tiktok", "facebook"],
                       help="Output formats")
    parser.add_argument("--api-key", help="OpenRouter API key (or set OPENROUTER_KEY env)")

    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENROUTER_KEY")
    if not api_key:
        print("❌ No API key provided. Set OPENROUTER_KEY or use --api-key")
        sys.exit(1)

    recapper = MangaRecapper(api_key)
    success = recapper.run(args.url, args.formats)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
