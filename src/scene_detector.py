"""
scene_detector.py
Detects shot boundaries and analyzes visual content per scene.
"""
import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple
import subprocess
import json

@dataclass
class Scene:
    start_time: float
    end_time: float
    duration: float
    complexity_score: float  # Visual action/density score
    is_action_scene: bool
    frame_path: Path

class SceneDetector:
    def __init__(self, video_path: Path, work_dir: Path):
        self.video_path = video_path
        self.work_dir = work_dir
        self.scenes: List[Scene] = []

    def detect_scenes(self, threshold: float = 30.0) -> List[Scene]:
        """Detect scene changes using histogram comparison."""
        print(f"🔍 Opening video: {self.video_path}")
        cap = cv2.VideoCapture(str(self.video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        prev_hist = None
        scene_starts = [0.0]  # First scene starts at 0

        frame_idx = 0
        print("🔍 Analyzing frames for scene changes...")
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"✅ Frame analysis complete. Processed {frame_idx} frames")
                break
            frame_idx += 1
            if frame_idx % 100 == 0:
                print(f"   Processed {frame_idx} frames...")

            # Sample every 2 frames for speed
            if frame_idx % 2 == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                hist = cv2.calcHist([gray], [0], None, [64], [0, 256])

                if prev_hist is not None:
                    diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CHISQR)
                    if diff > threshold:
                        scene_starts.append(frame_idx / fps)

                prev_hist = hist
            frame_idx += 1

        cap.release()

        # Create scene segments
        duration = total_frames / fps
        for i in range(len(scene_starts)):
            start = scene_starts[i]
            end = scene_starts[i + 1] if i + 1 < len(scene_starts) else duration

            # Extract representative frame
            mid_time = (start + end) / 2
            frame_path = self._extract_frame(mid_time)

            # Analyze complexity
            complexity = self._analyze_complexity(frame_path)

            scene = Scene(
                start_time=start,
                end_time=end,
                duration=end - start,
                complexity_score=complexity,
                is_action_scene=complexity > 0.6,  # Threshold for "badass" scenes
                frame_path=frame_path
            )
            self.scenes.append(scene)

        print(f"✅ Detected {len(self.scenes)} scenes")
        return self.scenes

    def _extract_frame(self, timestamp: float) -> Path:
        """Extract a frame at specific timestamp."""
        output = self.work_dir / f"scene_frame_{timestamp:.2f}.jpg"
        cmd = [
            "ffmpeg", "-y", "-ss", str(timestamp),
            "-i", str(self.video_path),
            "-vframes", "1", "-q:v", "2",
            str(output)
        ]
        subprocess.run(cmd, capture_output=True)
        return output

    def _analyze_complexity(self, frame_path: Path) -> float:
        """Score visual complexity (action = high complexity)."""
        if not frame_path.exists():
            return 0.5

        img = cv2.imread(str(frame_path))
        if img is None:
            return 0.5

        # Edge density = action/complexity indicator
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])

        # Color variance = visual richness
        color_var = np.std(img.reshape(-1, 3), axis=0).mean()

        # Combine scores (normalize to 0-1)
        score = min(1.0, (edge_density * 3 + color_var / 50) / 2)
        return score

    def get_action_scenes(self) -> List[Scene]:
        """Return only high-complexity scenes."""
        return [s for s in self.scenes if s.is_action_scene]

    def save_scene_data(self):
        """Save scene info for debugging."""
        data = [
            {
                "start": float(s.start_time),
                "end": float(s.end_time),
                "duration": float(s.duration),
                "complexity": float(s.complexity_score),
                "is_action": bool(s.is_action_scene)
            }
            for s in self.scenes
        ]
        with open(self.work_dir / "scenes.json", "w") as f:
            json.dump(data, f, indent=2)
