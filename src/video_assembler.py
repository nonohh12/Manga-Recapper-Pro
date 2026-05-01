"""
video_assembler.py
Assembles final video with precise scene-narration sync.
"""
import subprocess
import json
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
import os

@dataclass
class VideoFormat:
    name: str
    width: int
    height: int
    crop_filter: str

FORMATS = {
    "youtube": VideoFormat("youtube", 1920, 1080, "scale=1920:1080"),
    "youtube_shorts": VideoFormat("youtube_shorts", 1080, 1920, "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"),
    "instagram": VideoFormat("instagram", 1080, 1080, "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2"),
    "facebook": VideoFormat("facebook", 1280, 720, "scale=1280:720"),
    "tiktok": VideoFormat("tiktok", 1080, 1920, "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2")
}

class VideoAssembler:
    def __init__(self, video_path: Path, work_dir: Path, output_dir: Path):
        self.video_path = video_path
        self.work_dir = work_dir
        self.output_dir = output_dir

    def assemble(
        self,
        scenes: List[Dict],
        tts_segments: List[Dict],
        target_format: str = "youtube",
        watermark_regions: List[Dict] = None,
        bgm_path: Path = None,
        output_name: str = "final_recap"
    ) -> Path:
        """
        Assemble video with scene-synced narration.

        Key improvement: Each scene is extracted, narration is overlaid,
        then scenes are concatenated in order.
        """
        fmt = FORMATS.get(target_format, FORMATS["youtube"])

        # Step 1: Extract each scene as individual clip
        scene_clips = self._extract_scenes(scenes, watermark_regions, fmt)

        # Step 2: Add narration to each scene clip
        narrated_clips = self._add_narration_to_scenes(scene_clips, tts_segments)

        # Step 3: Concatenate all scenes
        final_video = self._concatenate_scenes(narrated_clips, fmt, output_name)

        # Step 4: Add BGM if provided
        if bgm_path and bgm_path.exists():
            final_video = self._add_bgm(final_video, bgm_path, output_name)

        return final_video

    def _extract_scenes(
        self, 
        scenes: List[Dict], 
        watermark_regions: List[Dict],
        fmt: VideoFormat
    ) -> List[Path]:
        """Extract each scene as a separate video file."""
        clips = []

        for i, scene in enumerate(scenes):
            start = scene["start"]
            end = scene["end"]
            duration = end - start

            output = self.work_dir / f"scene_clip_{i:03d}.mp4"

            # Build video filter
            vf_parts = []

            # FIXED: Add watermark removal FIRST (on original dimensions)
            if watermark_regions:
                for region in watermark_regions:
                    x, y, w, h = region["x"], region["y"], region["w"], region["h"]
                    vf_parts.append(f"delogo=x={x}:y={y}:w={w}:h={h}")

            # FIXED: Add scaling/cropping AFTER removing watermarks
            if fmt.crop_filter:
                vf_parts.append(fmt.crop_filter)

            vf = ",".join(vf_parts)

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-t", str(duration),
                "-i", str(self.video_path),
                "-vf", vf,
                "-c:v", "libx264", "-preset", "fast",
                "-crf", "23",
                "-an",  # No audio yet
                str(output)
            ]

            subprocess.run(cmd, capture_output=True, check=True)
            clips.append(output)

        print(f"✅ Extracted {len(clips)} scene clips")
        return clips

    def _add_narration_to_scenes(
        self, 
        scene_clips: List[Path], 
        tts_segments: List[Dict]
    ) -> List[Path]:
        """Add TTS narration to each scene clip."""
        narrated = []

        for i, clip in enumerate(scene_clips):
            if i >= len(tts_segments):
                # No narration for this scene, keep silent
                narrated.append(clip)
                continue

            tts = tts_segments[i]
            tts_path = Path(tts["output_path"])

            if not tts_path.exists():
                narrated.append(clip)
                continue

            output = self.work_dir / f"scene_narrated_{i:03d}.mp4"

            # Get scene duration
            scene_duration = self._get_video_duration(clip)
            tts_duration = self._get_audio_duration(tts_path)

            # If TTS is longer than scene, speed it up slightly
            if tts_duration > scene_duration and scene_duration > 0:
                speed_factor = tts_duration / scene_duration
                # Limit speed to reasonable range
                speed_factor = min(max(speed_factor, 0.8), 1.3)
                atempo = f"atempo={1/speed_factor}"
            else:
                atempo = "atempo=1.0"

            # Mix video with narration
            cmd = [
                "ffmpeg", "-y",
                "-i", str(clip),
                "-i", str(tts_path),
                "-filter_complex",
                f"[1:a]{atempo},volume=2.0[aout]",  # FIXED: Applied filters to audio stream only
                "-map", "0:v",                      # FIXED: Video stream map First
                "-map", "[aout]",                   # FIXED: Audio stream map Second
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                str(output)
            ]

            subprocess.run(cmd, capture_output=True, check=True)
            narrated.append(output)

        print(f"✅ Added narration to {len(narrated)} scenes")
        return narrated

    def _concatenate_scenes(
        self, 
        clips: List[Path], 
        fmt: VideoFormat,
        output_name: str
    ) -> Path:
        """Concatenate all scene clips into final video."""
        # Create concat demuxer file
        concat_file = self.work_dir / "concat_list.txt"

        with open(concat_file, "w") as f:
            for clip in clips:
                # FIXED: Force absolute pathing to avoid ffmpeg No Such File errors
                f.write(f"file '{clip.absolute()}'\n")

        output = self.output_dir / f"{output_name}_{fmt.name}.mp4"

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output)
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        print(f"✅ Assembled final video: {output}")
        return output

    def _add_bgm(self, video_path: Path, bgm_path: Path, output_name: str) -> Path:
        """Add background music with ducking."""
        output = self.output_dir / f"{output_name}_with_bgm.mp4"

        # Audio ducking: lower BGM when narration is present
        filter_complex = (
            "[1:a]volume=0.15[bgm];"
            "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-stream_loop", "-1", "-i", str(bgm_path),
            "-filter_complex", filter_complex,
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(output)
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        print(f"✅ Added BGM: {output}")
        return output

    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json", str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(json.loads(result.stdout)["format"]["duration"])
        except:
            return 0.0

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json", str(audio_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(json.loads(result.stdout)["format"]["duration"])
        except:
            return 0.0

    def generate_all_formats(
        self,
        scenes: List[Dict],
        tts_segments: List[Dict],
        watermark_regions: List[Dict] = None,
        bgm_path: Path = None,
        output_name: str = "final_recap"
    ) -> Dict[str, Path]:
        """Generate output in all supported formats."""
        results = {}

        for format_name in ["youtube", "youtube_shorts", "instagram", "tiktok"]:
            print(f"\n🎬 Generating {format_name} format...")

            path = self.assemble(
                scenes, tts_segments, format_name,
                watermark_regions, bgm_path, f"{output_name}_{format_name}"
            )
            results[format_name] = path

        return results
