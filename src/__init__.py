"""
Manga Recapper Pro - Temporal Sync Edition

A complete pipeline for automatically generating narrated recap videos
from manga/manhwa content with precise scene-audio synchronization.
"""

__version__ = "2.0.0"
__author__ = "AI Pipeline"

from .scene_detector import SceneDetector, Scene
from .audio_processor import AudioProcessor, AudioSegment
from .script_generator import ScriptGenerator, SceneScript
from .tts_engine import TTSEngine, TTSSegment
from .video_assembler import VideoAssembler, FORMATS

__all__ = [
    "SceneDetector", "Scene",
    "AudioProcessor", "AudioSegment", 
    "ScriptGenerator", "SceneScript",
    "TTSEngine", "TTSSegment",
    "VideoAssembler", "FORMATS"
]
