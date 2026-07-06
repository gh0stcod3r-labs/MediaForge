"""Video file scanning for MediaForge Organizer."""

from pathlib import Path
from typing import Optional
from .models import VideoFile, MediaType


SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".m4v"}


class VideoScanner:
    """Scans directories for video files."""
    
    @staticmethod
    def scan_directory(source_path: Path, media_type: Optional[MediaType] = None) -> list[VideoFile]:
        """Scan a directory for video files."""
        if not source_path.is_dir():
            return []
        
        videos = []
        for file_path in source_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                video = VideoFile(
                    path=file_path,
                    filename=file_path.name,
                    size=file_path.stat().st_size,
                    media_type=media_type,
                )
                videos.append(video)
        
        return videos
    
    @staticmethod
    def validate_path(path: Path) -> bool:
        """Validate that a path exists and is readable."""
        return path.exists() and path.is_dir()
