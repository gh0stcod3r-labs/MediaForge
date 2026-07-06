"""Offline provider - parses title from filename without internet."""

from pathlib import Path
from typing import Optional

from . import BaseProvider, ProviderResponse, ProviderStatus
from ..matcher import AdvancedMatcher


class OfflineProvider(BaseProvider):
    """Local filename parser - works without internet."""
    
    @property
    def provider_name(self) -> str:
        return "Offline"
    
    @property
    def requires_api_key(self) -> bool:
        return False
    
    def search(self, query: str, source_path: Optional[Path] = None) -> ProviderResponse:
        """Parse filename to extract metadata.
        
        Args:
            query: Filename to parse
            source_path: Source file path (for MatchResult) - accepted for
                interface parity with the other providers, all of which are
                called uniformly as search(query, source_path) by
                ProviderSelector.search_with_fallback.
            
        Returns:
            ProviderResponse with parsed metadata
        """
        try:
            matcher = AdvancedMatcher()
            result = matcher.parse_filename(query)
            
            if result:
                match = self._create_match_result(
                    title=result.get("title", "Unknown"),
                    confidence=result.get("confidence", 0.8),
                    season=result.get("season"),
                    episode=result.get("episode"),
                    year=result.get("year"),
                    source_path=source_path,
                    filename=query,
                )
                return ProviderResponse(
                    status=ProviderStatus.OK,
                    matches=[match],
                )
            else:
                return ProviderResponse(
                    status=ProviderStatus.NOT_FOUND,
                    error_message="Could not parse filename",
                )
        
        except Exception as e:
            return ProviderResponse(
                status=ProviderStatus.ERROR,
                error_message=str(e),
            )
    
    def test_connection(self) -> bool:
        """Offline provider always works."""
        return True
