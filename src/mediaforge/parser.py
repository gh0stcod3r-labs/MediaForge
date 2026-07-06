"""Filename and metadata parsing for MediaForge Organizer."""

import re
from typing import Optional, Tuple
from .models import VideoFile


class VideoParser:
    """Parses video filenames to extract metadata."""
    
    # Patterns for common filename formats
    ANIME_PATTERN = r"\[?\w+\]?\s*(?P<title>.*?)\s*-\s*(?P<episode>\d+)"
    TV_SHOW_PATTERN = r"(?P<title>.*?)\s*-?\s*[Ss](?P<season>\d+)[Ee](?P<episode>\d+)"
    MOVIE_PATTERN = r"(?P<title>.*?)\s*\((?P<year>\d{4})\)"
    
    @staticmethod
    def parse_title(filename: str) -> Optional[str]:
        """Extract title from filename, removing common suffixes."""
        # Remove extension
        name = filename.rsplit(".", 1)[0]
        
        # Remove quality tags and resolution
        name = re.sub(r"\[.*?\]|\{.*?\}|1080p|720p|480p|4K|DL|HDTV|Web-DL", "", name, flags=re.IGNORECASE)
        
        # Remove extra spaces
        name = re.sub(r"\s+", " ", name).strip()
        
        return name if name else None
    
    @staticmethod
    def parse_episode(filename: str) -> Optional[Tuple[int, int]]:
        """Extract season and episode numbers from filename."""
        # Try S##E## format
        match = re.search(r"[Ss](\d+)[Ee](\d+)", filename)
        if match:
            season, episode = match.groups()
            return (int(season), int(episode))
        return None
    
    @staticmethod
    def parse_year(filename: str) -> Optional[int]:
        """Extract year from filename."""
        match = re.search(r"\((\d{4})\)", filename)
        if match:
            year = match.group(1)
            return int(year)
        return None
    
    @classmethod
    def parse_video(cls, video: VideoFile) -> VideoFile:
        """Parse a video file and extract metadata."""
        filename = video.filename
        
        video.title = cls.parse_title(filename)
        
        episode_match = cls.parse_episode(filename)
        if episode_match:
            video.season, video.episode = episode_match
        
        video.year = cls.parse_year(filename)
        
        return video
