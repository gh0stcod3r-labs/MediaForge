"""Base provider class for metadata matching."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, List
from pathlib import Path
from dataclasses import dataclass

from ..match_result import MatchResult, MatchProvider


class ProviderStatus(Enum):
    """Provider operation status."""
    OK = "ok"
    NO_INTERNET = "no_internet"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    INVALID_KEY = "invalid_key"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass
class ProviderResponse:
    """Response from a provider lookup."""
    status: ProviderStatus
    matches: List[MatchResult] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.matches is None:
            self.matches = []
    
    def is_success(self) -> bool:
        """Check if lookup was successful."""
        return self.status == ProviderStatus.OK and len(self.matches) > 0


class BaseProvider(ABC):
    """Abstract base class for metadata providers."""
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 5):
        """Initialize provider.
        
        Args:
            api_key: Optional API key for provider
            timeout: Request timeout in seconds (default 5)
        """
        self.api_key = api_key
        self.timeout = timeout
        self.name = self.__class__.__name__
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get user-friendly provider name."""
        pass
    
    @property
    @abstractmethod
    def requires_api_key(self) -> bool:
        """Whether this provider requires an API key."""
        pass
    
    @abstractmethod
    def search(self, query: str, source_path: Optional[Path] = None) -> ProviderResponse:
        """Search for a title.
        
        Args:
            query: Search query (title, filename, etc.)
            source_path: Source file path, used to populate MatchResult.source_path.
                Every provider implementation must accept this parameter -
                ProviderSelector.search_with_fallback calls search(query, source_path)
                uniformly for all providers in the chain, including this base signature.
            
        Returns:
            ProviderResponse with matches and status
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test provider connection and credentials.
        
        Returns:
            True if connection is valid
        """
        pass
    
    def validate_api_key(self, key: str) -> bool:
        """Validate API key format (can be overridden by subclasses).
        
        Args:
            key: API key to validate
            
        Returns:
            True if key format looks valid
        """
        return len(key) > 0

    def _provider_enum(self) -> MatchProvider:
        """Map provider implementation to MatchProvider enum."""
        name = self.provider_name.lower().strip()
        if "tmdb" in name:
            return MatchProvider.TMDB
        if "anilist" in name:
            return MatchProvider.ANILIST
        if "myanimelist" in name or name == "mal" or "jikan" in name:
            return MatchProvider.MAL
        if "tvmaze" in name:
            return MatchProvider.TVMAZE
        if "offline" in name:
            return MatchProvider.OFFLINE
        if "cleanup" in name:
            return MatchProvider.AI_CLEANUP
        return MatchProvider.MANUAL_INPUT
    
    def _create_match_result(
        self,
        title: str,
        confidence: float = 0.9,
        season: Optional[int] = None,
        episode: Optional[int] = None,
        year: Optional[int] = None,
        source_path = None,
        filename: Optional[str] = None,
    ) -> MatchResult:
        """Create a MatchResult from provider data.
        
        Args:
            title: Series/movie title
            confidence: Match confidence (0-1)
            season: Season number (for TV)
            episode: Episode number (for TV)
            year: Year
            source_path: Source file path
            filename: Original filename
            
        Returns:
            MatchResult object
        """
        return MatchResult(
            source_path=source_path,
            filename=filename or "",
            provider=self._provider_enum(),
            confidence=confidence,
            title=title,
            series_name=title,
            season=season,
            episode=episode,
            year=year,
        )
