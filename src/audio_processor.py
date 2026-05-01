"""
audio_processor.py
Extracts and transcribes audio with timestamps.
Also analyzes audio energy to detect "intense" moments.
"""
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

try:
    import whisper
except ImportError:
    whisper = None

@dataclass
class AudioSegment:
    start: float
    end: float
    text: str
    audio_energy: float  # Volume/intensity

class AudioProcessor:
    def __init__(self, video_path: Path, work_dir: Path):
        self.video_path = video_path
        self.work_dir = work_dir
        self.audio_path = work_dir / "audio.wav"
        self.segments: List[AudioSegment] = []

    def extract_audio(self):
        """Extract audio to WAV for processing."""
        cmd = [
            "ffmpeg", "-y", "-i", str(self.video_path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(self.audio_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        print("✅ Audio extracted")

    def transcribe(self) -> List[AudioSegment]:
        """Transcribe with Whisper and add audio energy data."""
        if whisper is None:
            print("⚠️  Whisper not installed, skipping transcription")
            return []

        print("🎙️ Transcribing with Whisper...")
        model = whisper.load_model("base")  # Small but accurate enough
        result = model.transcribe(str(self.audio_path), language="en", verbose=False)

        # Analyze audio energy per segment
        audio_data = self._load_audio_data()

        for seg in result["segments"]:
            start = seg["start"]
            end = seg["end"]
            text = seg["text"].strip()

            # Calculate audio energy for this segment
            energy = self._calculate_energy(audio_data, start, end)

            self.segments.append(AudioSegment(
                start=start, end=end, text=text, audio_energy=energy
            ))

        print(f"✅ Transcribed {len(self.segments)} segments")
        return self.segments

    def _load_audio_data(self) -> np.ndarray:
        """Load raw audio data."""
        import wave
        with wave.open(str(self.audio_path), 'rb') as wf:
            data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        return data.astype(np.float32) / 32768.0

    def _calculate_energy(self, audio_data: np.ndarray, start: float, end: float) -> float:
        """Calculate RMS energy for a time segment."""
        sr = 16000
        start_sample = int(start * sr)
        end_sample = int(end * sr)

        if start_sample >= len(audio_data):
            return 0.0
        end_sample = min(end_sample, len(audio_data))

        segment = audio_data[start_sample:end_sample]
        if len(segment) == 0:
            return 0.0

        rms = np.sqrt(np.mean(segment ** 2))
        return float(rms)

    def get_intense_moments(self, threshold: float = 0.3) -> List[Dict]:
        """Find moments with high audio energy (screams, fights, etc)."""
        return [
            {"start": s.start, "end": s.end, "text": s.text, "energy": s.audio_energy}
            for s in self.segments if s.audio_energy > threshold
        ]

    def save_transcript(self):
        """Save transcript for debugging."""
        data = [
            {"start": float(s.start), "end": float(s.end), "text": s.text, "energy": float(s.audio_energy)}
            for s in self.segments
        ]
        with open(self.work_dir / "transcript.json", "w") as f:
            json.dump(data, f, indent=2)
