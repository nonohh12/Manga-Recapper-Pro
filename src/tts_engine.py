"""
tts_engine.py
Kokoro TTS integration for natural narration.
"""
import subprocess
import json
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
import tempfile
import os

try:
    from kokoro import KPipeline
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False
    print("⚠️  Kokoro not installed. Will use fallback TTS.")

@dataclass
class TTSSegment:
    text: str
    output_path: Path
    duration: float
    scene_start: float
    scene_end: float

class TTSEngine:
    def __init__(self, work_dir: Path, voice: str = "af_bella"):
        self.work_dir = work_dir
        self.voice = voice
        self.pipeline = None
        
        if KOKORO_AVAILABLE:
            try:
                self.pipeline = KPipeline(lang_code="a")
                print(f"✅ Kokoro TTS loaded with voice: {voice}")
            except Exception as e:
                print(f"⚠️  Failed to load Kokoro: {e}")
                
    def generate_segments(self, scripts: List[Dict], speed: float = 1.0) -> List[TTSSegment]:
        """Generate TTS for each scene script."""
        segments = []
        
        for i, script in enumerate(scripts):
            text = script["narration"]
            scene_start = script["scene_start"]
            scene_end = script["scene_end"]
            
            output_path = self.work_dir / f"tts_segment_{i:03d}.wav"
            
            if self.pipeline:
                duration = self._generate_kokoro(text, output_path, speed)
            else:
                duration = self._generate_fallback(text, output_path)
                
            segments.append(TTSSegment(
                text=text,
                output_path=output_path,
                duration=duration,
                scene_start=scene_start,
                scene_end=scene_end
            ))
            
        print(f"✅ Generated {len(segments)} TTS segments")
        return segments

    def _generate_kokoro(self, text: str, output_path: Path, speed: float) -> float:
        """Generate audio with Kokoro."""
        try:
            # Use newline split pattern
            split_pat = r"\n+"
            generator = self.pipeline(text, voice=self.voice, speed=speed, split_pattern=split_pat)
            
            # Collect all audio segments
            import torch
            audio_segments = []
            for _, _, audio in generator:
                audio_segments.append(audio)
                
            if audio_segments:
                full_audio = torch.cat(audio_segments, dim=0)
                # Save as WAV
                import torchaudio
                torchaudio.save(str(output_path), full_audio.unsqueeze(0), 24000)
                
                # Calculate duration
                duration = len(full_audio) / 24000
                return duration
            else:
                return 0.0
                
        except Exception as e:
            print(f"⚠️  Kokoro failed: {e}, using fallback")
            return self._generate_fallback(text, output_path)

    def _generate_fallback(self, text: str, output_path: Path) -> float:
        """Fallback using espeak or pyttsx3."""
        try:
            # Try espeak-ng first
            cmd = [
                "espeak-ng", "-w", str(output_path),
                "-s", "150",
                "-p", "50",
                text
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 or not output_path.exists():
                self._create_silent_audio(output_path, len(text.split()) * 0.4)
                
            # Get duration with ffprobe
            duration = self._get_audio_duration(output_path)
            return duration
            
        except Exception as e:
            print(f"⚠️  Fallback TTS failed: {e}")
            self._create_silent_audio(output_path, len(text.split()) * 0.4)
            return len(text.split()) * 0.4

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio file duration using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                str(audio_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except:
            return 0.0

    def _create_silent_audio(self, output_path: Path, duration: float):
        """Create silent audio as last resort."""
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", str(duration),
            "-acodec", "pcm_s16le",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)

    def combine_segments(self, segments: List[TTSSegment], output_path: Path) -> float:
        """Combine all TTS segments into one file with gaps."""
        # Create a concat file
        concat_file = self.work_dir / "tts_concat.txt"
        
        with open(concat_file, "w") as f:
            for i, seg in enumerate(segments):
                # Add silence between segments if there is a gap
                if i > 0:
                    gap = seg.scene_start - segments[i-1].scene_end
                    if gap > 0.5:
                        silence_path = self.work_dir / f"silence_{i}.wav"
                        self._create_silent_audio(silence_path, gap)
                        line = "file  + str(silence_path) + \n"
                        f.write(line)
                        
                line = "file  + str(seg.output_path) + \n"
                f.write(line)
                
        # Concatenate
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        
        duration = self._get_audio_duration(output_path)
        print(f"✅ Combined TTS duration: {duration:.1f}s")
        return duration
