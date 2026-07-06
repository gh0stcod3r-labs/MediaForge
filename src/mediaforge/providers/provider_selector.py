"""Intelligent provider selection logic."""

from typing import List, Optional, Tuple
from pathlib import Path
import re
import logging

from . import BaseProvider, ProviderResponse, ProviderStatus
from .offline_provider import OfflineProvider
from .tmdb_provider import TMDBProvider
from .anilist_provider import AniListProvider
from .mal_provider import MALProvider
from .tvmaze_provider import TVMazeProvider
from ..config import get_settings


class MediaType:
    """Media type detection constants."""
    ANIME = "anime"
    TV = "tv"
    MOVIE = "movie"
    UNKNOWN = "unknown"


class ProviderSelector:
    """Intelligent provider selection based on media type."""
    
    def __init__(self):
        """Initialize provider selector with all available providers."""
        self.offline_provider = OfflineProvider()
        self.tmdb_provider = TMDBProvider()
        self.anilist_provider = AniListProvider()
        self.mal_provider = MALProvider()
        self.tvmaze_provider = TVMazeProvider()
        self.scorer = None
        self.logger = logging.getLogger(__name__)
    
    def get_media_type(self, filename: str) -> str:
        """Detect media type from filename patterns.
        
        Args:
            filename: Original filename
            
        Returns:
            MediaType constant (anime, tv, movie, unknown)
        """
        filename_lower = filename.lower()
        
        # Anime indicators
        anime_patterns = [
            r'\[.*?\]',  # Fansub groups in brackets
            r'(480|720|1080)p',  # Resolution tag (common in anime)
            r'(BD|Blu-ray|DVDRip)',  # Quality markers (anime releases)
            r'(10-bit|HEVC|x265)',  # Codec markers (anime releases)
            r'(FLAC|AAC)',  # Audio codec (anime releases)
            r'(season|s)\s*\d+',  # S01 pattern with "season" keyword
            r'(?:episode|ep|e)\s*\d+',  # Episode marker often in anime
            r'(480p|720p|1080p)',  # Resolution in different formats
        ]
        
        anime_score = 0
        for pattern in anime_patterns:
            if re.search(pattern, filename_lower):
                anime_score += 1
        
        # TV indicators
        tv_patterns = [
            r's\d{1,2}e\d{1,2}',  # S01E01 format (very common in TV)
            r'\d{1,2}x\d{1,2}',  # 1x01 format (common in TV)
        ]
        
        tv_score = 0
        for pattern in tv_patterns:
            if re.search(pattern, filename_lower):
                tv_score += 2  # Give TV patterns higher weight
        
        # Movie indicators
        movie_patterns = [
            r'\(20\d{2}\)',  # (2020) format common in movies
            r'720p|1080p|4K',  # HD markers in movies
            r'BluRay|DvdRip|HDRip',  # Movie release types
        ]
        
        movie_score = 0
        for pattern in movie_patterns:
            if re.search(pattern, filename_lower):
                movie_score += 1
        
        # Determine type based on scores
        if tv_score >= 2:  # Strong TV indicators
            return MediaType.TV
        elif anime_score >= 2:  # Strong anime indicators
            return MediaType.ANIME
        elif movie_score >= 2:  # Strong movie indicators
            return MediaType.MOVIE
        elif anime_score > 0:  # Some anime indicators
            return MediaType.ANIME
        elif tv_score > 0:  # Some TV indicators
            return MediaType.TV
        elif movie_score > 0:  # Some movie indicators
            return MediaType.MOVIE
        
        return MediaType.UNKNOWN
    
    def get_provider_chain(self, media_type: str, selected_provider: Optional[str] = None) -> List[BaseProvider]:
        """Get ordered provider chain for media type.
        
        Args:
            media_type: Detected media type
            
        Returns:
            Ordered list of providers to try
        """
        provider = (selected_provider or get_settings().get_provider() or "automatic").strip().lower()

        if provider in {"automatic", "auto"}:
            if media_type == MediaType.ANIME:
                return [self.anilist_provider, self.mal_provider, self.tmdb_provider, self.offline_provider]
            if media_type == MediaType.TV:
                return [self.tmdb_provider, self.tvmaze_provider, self.offline_provider]
            if media_type == MediaType.MOVIE:
                return [self.tmdb_provider, self.offline_provider]
            return [self.anilist_provider, self.mal_provider, self.tmdb_provider, self.tvmaze_provider, self.offline_provider]

        if provider == "tmdb":
            return [self.tmdb_provider]
        if provider in {"anilist"}:
            return [self.anilist_provider]
        if provider in {"myanimelist", "mal", "jikan"}:
            return [self.mal_provider]
        if provider == "tvmaze":
            return [self.tvmaze_provider]
        if provider == "offline":
            return [self.offline_provider]

        return [self.offline_provider]
    
    def search_with_fallback(self, filename: str, 
                            source_path: Optional[Path] = None,
                            selected_provider: Optional[str] = None) -> Tuple[ProviderResponse, str]:
        """Search for match with automatic fallback chain.
        
        Args:
            filename: Original filename
            source_path: Source file path
            
        Returns:
            Tuple of (ProviderResponse, provider_name_used)
        """
        media_type = self.get_media_type(filename)
        providers = self.get_provider_chain(media_type, selected_provider)
        
        for provider in providers:
            try:
                self.logger.info(
                    "Provider request: provider=%s query=%s endpoint=%s",
                    provider.provider_name, filename, getattr(provider, "api_base", "n/a"),
                )
                response = provider.search(filename, source_path)
                self.logger.info(
                    "Provider response: provider=%s query=%s status=%s result_count=%d error=%s",
                    provider.provider_name, filename, response.status.value,
                    len(response.matches), response.error_message,
                )
                if response.matches:
                    selected = response.matches[0]
                    self.logger.info(
                        "Provider selected: provider=%s query=%s final_provider=%s confidence=%.2f",
                        provider.provider_name, filename, selected.provider.value, selected.confidence,
                    )
                    return response, provider.provider_name
                if selected_provider and selected_provider.lower() not in {"automatic", "auto"}:
                    return response, provider.provider_name
            except Exception as exc:
                self.logger.warning("Provider %s failed for %s: %s", provider.provider_name, filename, exc)
                if selected_provider and selected_provider.lower() not in {"automatic", "auto"}:
                    return ProviderResponse(
                        status=ProviderStatus.ERROR,
                        error_message=str(exc),
                    ), provider.provider_name
                continue
        
        # If all else fails, return offline result
        response = self.offline_provider.search(filename, source_path)
        return response, self.offline_provider.provider_name
    
    def get_provider_by_name(self, name: str) -> Optional[BaseProvider]:
        """Get provider instance by name.
        
        Args:
            name: Provider name (e.g., "TMDB", "AniList")
            
        Returns:
            Provider instance or None
        """
        name_lower = name.lower()
        
        if "tmdb" in name_lower:
            return self.tmdb_provider
        elif "anilist" in name_lower:
            return self.anilist_provider
        elif "mal" in name_lower or "myanimelist" in name_lower:
            return self.mal_provider
        elif "tvmaze" in name_lower:
            return self.tvmaze_provider
        elif "offline" in name_lower:
            return self.offline_provider
        
        return None
