"""TVMaze provider for TV series metadata."""

import requests
from typing import Optional, List
from pathlib import Path

from . import BaseProvider, ProviderStatus, ProviderResponse
from ..match_result import MatchResult, MatchProvider
from ..cache import get_cache
from ..matcher import AdvancedMatcher
from .scoring import ConfidenceScorer, fuzzy_match


TVMAZE_API_BASE = "https://api.tvmaze.com"
TVMAZE_REQUEST_TIMEOUT = 5


class TVMazeProvider(BaseProvider):
    """TVMaze provider for TV series metadata."""

    api_base = TVMAZE_API_BASE  # exposed for centralized provider-lookup logging
    
    @property
    def provider_name(self) -> str:
        return "TVMaze"
    
    @property
    def requires_api_key(self) -> bool:
        """TVMaze doesn't require an API key."""
        return False
    
    def test_connection(self) -> bool:
        """Test TVMaze API connection.
        
        TVMaze doesn't require authentication, so always return True if reachable.
        
        Returns:
            True if API is reachable
        """
        try:
            response = requests.get(
                f"{TVMAZE_API_BASE}/shows",
                params={"page": 0},
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def search(self, query: str, source_path: Optional[Path] = None) -> ProviderResponse:
        """Search for TV series.
        
        Args:
            query: Search query
            source_path: Source file path (for MatchResult)
            
        Returns:
            ProviderResponse with matches or error
        """
        # Check cache first
        cache = get_cache()
        cached = cache.get("TVMaze", query)
        if cached:
            return ProviderResponse(
                status=ProviderStatus.OK,
                matches=cached.get("matches", [])
            )
        
        try:
            matches = self._search_shows(query)
            
            if not matches:
                return ProviderResponse(
                    status=ProviderStatus.NOT_FOUND,
                    error_message=f"No TV series found for: {query}"
                )
            
            # Cache results
            cache.set("TVMaze", query, {"matches": matches})
            
            return ProviderResponse(
                status=ProviderStatus.OK,
                matches=matches
            )
        
        except requests.Timeout:
            return ProviderResponse(
                status=ProviderStatus.TIMEOUT,
                error_message=f"TVMaze request timed out after {TVMAZE_REQUEST_TIMEOUT}s"
            )
        except requests.exceptions.ConnectionError:
            return ProviderResponse(
                status=ProviderStatus.NO_INTERNET,
                error_message="No internet connection available"
            )
        except Exception as e:
            return ProviderResponse(
                status=ProviderStatus.ERROR,
                error_message=f"TVMaze API error: {str(e)}"
            )
    
    def _search_shows(self, query: str) -> List[Optional[MatchResult]]:
        """Search for TV shows using TVMaze API.
        
        Args:
            query: Search query
            
        Returns:
            List of MatchResult objects
        """
        try:
            response = requests.get(
                f"{TVMAZE_API_BASE}/search/shows",
                params={"q": query},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data[:5]:  # Top 5 results
                show = item.get("show", {})
                match = self._build_show_match(show, query)
                if match:
                    results.append(match)
            
            return results
        except Exception:
            return []
    
    def _build_show_match(self, item: dict, query: str) -> Optional[MatchResult]:
        """Build MatchResult from TV show result.
        
        Args:
            item: TVMaze show object
            query: Original search query
            
        Returns:
            MatchResult or None if invalid
        """
        try:
            title = item.get("name", "")
            if not title:
                return None

            parsed = AdvancedMatcher().parse_filename(query) or {}
            
            year = None
            premiered = item.get("premiered", "")
            if premiered:
                try:
                    year = int(premiered[:4])
                except (ValueError, TypeError):
                    pass
            if parsed.get("year") and not year:
                year = parsed.get("year")
            season = parsed.get("season")
            episode = parsed.get("episode")
            
            # Calculate confidence
            scorer = ConfidenceScorer()
            title_match = fuzzy_match(title, query)
            
            confidence = scorer.calculate(
                title_match=title_match > 0.95,
                title_fuzzy_ratio=title_match if title_match <= 0.95 else None,
                season_match=season is not None,
                episode_match=episode is not None,
                year_match=(year is not None),
                has_episode_info=episode is not None
            )
            
            return MatchResult(
                source_path=Path(query),
                filename=query,
                provider=MatchProvider.TVMAZE,
                confidence=confidence,
                title=title,
                series_name=title,
                season=season,
                episode=episode,
                year=year
            )
        except Exception:
            return None
