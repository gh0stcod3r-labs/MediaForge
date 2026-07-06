"""Data models for MediaForge Organizer."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


class MediaType(Enum):
    """Supported media categories."""
    ANIME = "Anime"
    TV_SHOW = "TV Show"
    MOVIE = "Movie"
    SPORTS = "Sports"
    CLIPS = "Clips"
    CREATOR_FOOTAGE = "Creator Footage"
    OTHER = "Other"


@dataclass
class VideoFile:
    """Represents a video file to be organized."""
    path: Path
    filename: str
    size: int
    media_type: Optional[MediaType] = None
    target_path: Optional[Path] = None
    title: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    year: Optional[int] = None

