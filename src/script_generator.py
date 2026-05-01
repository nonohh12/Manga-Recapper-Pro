"""
script_generator.py
Generates narration scripts per scene with temporal constraints.
"""
import requests
import json
from pathlib import Path
from typing import List, Dict
import base64
from dataclasses import dataclass

@dataclass
class SceneScript:
    scene_start: float
    scene_end: float
    duration: float
    narration: str
    word_count: int
    is_action: bool

class ScriptGenerator:
    def __init__(self, api_key: str, work_dir: Path):
        self.api_key = api_key
        self.work_dir = work_dir
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def generate_per_scene(
        self, 
        scenes: List[Dict], 
        transcript_segments: List[Dict],
        video_context: str = ""
    ) -> List[SceneScript]:
        """
        Generate narration for EACH scene individually.
        This ensures temporal sync.
        """
        scene_scripts = []

        for i, scene in enumerate(scenes):
            # Find transcript segments within this scene
            scene_text = self._get_scene_transcript(scene, transcript_segments)

            # Calculate max words for this scene's duration
            # Average speaking rate: 150 words per minute = 2.5 words/sec
            max_words = int(scene["duration"] * 2.2)  # Slightly slower for dramatic effect
            min_words = max(10, int(scene["duration"] * 1.5))  # Minimum to avoid silence

            # Get frame for visual context
            frame_path = Path(scene.get("frame_path", ""))

            narration = self._generate_scene_narration(
                scene=scene,
                scene_text=scene_text,
                frame_path=frame_path,
                max_words=max_words,
                min_words=min_words,
                scene_number=i + 1,
                total_scenes=len(scenes),
                video_context=video_context
            )

            word_count = len(narration.split())

            scene_scripts.append(SceneScript(
                scene_start=scene["start"],
                scene_end=scene["end"],
                duration=scene["duration"],
                narration=narration,
                word_count=word_count,
                is_action=scene.get("is_action", False)
            ))

            print(f"📝 Scene {i+1}/{len(scenes)}: {word_count} words for {scene['duration']:.1f}s")

        return scene_scripts

    def _get_scene_transcript(self, scene: Dict, transcript_segments: List[Dict]) -> str:
        """Get original transcript text for this scene."""
        scene_start = scene["start"]
        scene_end = scene["end"]

        texts = []
        for seg in transcript_segments:
            # Check overlap
            if seg["end"] > scene_start and seg["start"] < scene_end:
                texts.append(seg["text"])

        return " ".join(texts) if texts else "No original audio"

    def _generate_scene_narration(
        self,
        scene: Dict,
        scene_text: str,
        frame_path: Path,
        max_words: int,
        min_words: int,
        scene_number: int,
        total_scenes: int,
        video_context: str
    ) -> str:
        """Generate narration for a single scene using vision + context."""

        # Build prompt with strict constraints
        prompt = f"""You are a BADASS manga/manhwa narrator. Write FIRST-PERSON narration.

STORY CONTEXT: {video_context}
ORIGINAL SCENE AUDIO: {scene_text}
SCENE: {scene_number} of {total_scenes}
SCENE TYPE: {"ACTION/INTENSE" if scene.get("is_action") else "STORY/EXPOSITION"}

CRITICAL RULES:
1. Write EXACTLY {min_words}-{max_words} words (scene is {scene["duration"]:.1f} seconds long)
2. FIRST-PERSON perspective: "I", "my", "me"
3. BADASS, intense, dramatic tone
4. NO filler words: "Here is", "Based on", "Narrator:", "Script:", "In this scene"
5. Start IMMEDIATELY with the action
6. Match the emotion of the scene type
7. End with a hook if it's an action scene

Write the narration now:"""

        # Prepare message content
        content = [{"type": "text", "text": prompt}]

        # Add frame image if available
        if frame_path and frame_path.exists():
            with open(frame_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
            })

        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {
            "model": "google/gemini-2.0-flash-001",
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.7
        }

        try:
            r = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            res = r.json()
            narration = res["choices"][0]["message"]["content"]

            # Clean up
            for unwanted in [
                "Here is the script", "Based on the frames", "Narrator:",
                "Script:", "In this scene", "Here is", "Here are",
                "The narration:", "Narration:"
            ]:
                narration = narration.replace(unwanted, "")

            narration = narration.strip().strip('"').strip("'")

            # Word count check
            words = narration.split()
            if len(words) > max_words:
                # Truncate but keep sentences intact
                narration = self._truncate_to_words(narration, max_words)
            elif len(words) < min_words and len(words) > 0:
                # Extend with dramatic filler if too short
                narration = self._extend_narration(narration, min_words)

            return narration.strip()

        except Exception as e:
            print(f"⚠️  API error for scene {scene_number}: {e}")
            return self._fallback_narration(scene, min_words, max_words)

    def _truncate_to_words(self, text: str, max_words: int) -> str:
        """Truncate to max words, keeping last complete sentence."""
        words = text.split()
        if len(words) <= max_words:
            return text

        truncated = " ".join(words[:max_words])
        # Find last sentence end
        last_period = truncated.rfind(".")
        if last_period > len(truncated) * 0.7:  # Keep if we have most of the text
            return truncated[:last_period + 1]
        return truncated

    def _extend_narration(self, text: str, min_words: int) -> str:
        """Add dramatic extensions if too short."""
        current_words = len(text.split())
        needed = min_words - current_words

        extensions = [
            "I won't back down.",
            "This is my moment.",
            "They have no idea what's coming.",
            "My power is awakening.",
            "This ends now.",
            "I can feel the energy surging.",
            "No one stands in my way."
        ]

        import random
        while len(text.split()) < min_words and extensions:
            ext = random.choice(extensions)
            text += " " + ext
            extensions.remove(ext)

        return text

    def _fallback_narration(self, scene: Dict, min_words: int, max_words: int) -> str:
        """Fallback if API fails."""
        return "The power within me grows. I can feel it. This is only the beginning."

    def save_scripts(self, scripts: List[SceneScript]):
        """Save all scripts for debugging."""
        data = [
            {
                "start": float(s.scene_start),
                "end": float(s.scene_end),
                "duration": float(s.duration),
                "word_count": int(s.word_count),
                "is_action": bool(s.is_action),
                "narration": s.narration
            }
            for s in scripts
        ]
        with open(self.work_dir / "scripts.json", "w") as f:
            json.dump(data, f, indent=2)
