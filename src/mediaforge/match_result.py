"""Match engine results for MediaForge Organizer."""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from enum import Enum


class MatchProvider(Enum):
    """Source of match/rename information."""
    OFFLINE = "Offline"
    TMDB = "TMDB"
    ANILIST = "AniList"
    MAL = "Jikan"
    TVMAZE = "TVMaze"
    MANUAL_INPUT = "Manual"
    AI_CLEANUP = "AI Cleanup"


@dataclass
class MatchResult:
    """Result of matching/parsing a video file."""
    
    source_path: Path
    filename: str
    
    # Match information
    provider: MatchProvider
    confidence: float  # 0.0 to 1.0
    
    # Parsed metadata
    title: str
    series_name: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = None
    year: Optional[int] = None
    proposed_filename: Optional[str] = None
    status: str = "Matched"
    error_message: Optional[str] = None
    
    # Destination info
    destination_root: Optional[Path] = None
    destination_path: Optional[Path] = None
    
    def __post_init__(self):
        """Ensure confidence is 0-1 range."""
        if not self.series_name:
            self.series_name = self.title
        if not self.title:
            self.title = self.series_name or ""
        if not 0.0 <= self.confidence <= 1.0:
            self.confidence = max(0.0, min(1.0, self.confidence))
