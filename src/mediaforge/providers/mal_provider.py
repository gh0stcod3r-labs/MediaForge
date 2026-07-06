"""MyAnimeList provider using Jikan API for anime metadata."""

import requests
from typing import Optional, List
from pathlib import Path

from . import BaseProvider, ProviderStatus, ProviderResponse
from ..match_result import MatchResult, MatchProvider
from ..cache import get_cache
from ..matcher import AdvancedMatcher
from .scoring import ConfidenceScorer, fuzzy_match


JIKAN_API_BASE = "https://api.jikan.moe/v4"
JIKAN_REQUEST_TIMEOUT = 5


class MALProvider(BaseProvider):
    """MyAnimeList provider using Jikan API for anime metadata."""

    api_base = JIKAN_API_BASE  # exposed for centralized provider-lookup logging
    
    @property
    def provider_name(self) -> str:
        return "Jikan"
    
    @property
    def requires_api_key(self) -> bool:
        """Jikan doesn't require an API key."""
        return False
    
    def test_connection(self) -> bool:
        """Test Jikan API connection.
        
        Jikan doesn't require authentication, so always return True if reachable.
        
        Returns:
            True if API is reachable
        """
        try:
            response = requests.get(
                f"{JIKAN_API_BASE}/seasons",
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def search(self, query: str, source_path: Optional[Path] = None) -> ProviderResponse:
        """Search for anime.
        
        Args:
            query: Search query
            source_path: Source file path (for MatchResult)
            
        Returns:
            ProviderResponse with matches or error
        """
        # Check cache first
        cache = get_cache()
        cached = cache.get("MAL", query)
        if cached:
            return ProviderResponse(
                status=ProviderStatus.OK,
                matches=cached.get("matches", [])
            )
        
        try:
            matches = self._search_anime(query)
            
            if not matches:
                return ProviderResponse(
                    status=ProviderStatus.NOT_FOUND,
                    error_message=f"No anime found for: {query}"
                )
            
            # Cache results
            cache.set("MAL", query, {"matches": matches})
            
            return ProviderResponse(
                status=ProviderStatus.OK,
                matches=matches
            )
        
        except requests.Timeout:
            return ProviderResponse(
                status=ProviderStatus.TIMEOUT,
                error_message=f"Jikan request timed out after {JIKAN_REQUEST_TIMEOUT}s"
            )
        except requests.exceptions.ConnectionError:
            return ProviderResponse(
                status=ProviderStatus.NO_INTERNET,
                error_message="No internet connection available"
            )
        except Exception as e:
            return ProviderResponse(
                status=ProviderStatus.ERROR,
                error_message=f"Jikan API error: {str(e)}"
            )
    
    def _search_anime(self, query: str) -> List[Optional[MatchResult]]:
        """Search for anime using Jikan API.
        
        Args:
            query: Search query
            
        Returns:
            List of MatchResult objects
        """
        try:
            response = requests.get(
                f"{JIKAN_API_BASE}/anime",
                params={"query": query, "limit": 5},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("data", []):
                match = self._build_anime_match(item, query)
                if match:
                    results.append(match)
            
            return results
        except Exception:
            return []
    
    def _build_anime_match(self, item: dict, query: str) -> Optional[MatchResult]:
        """Build MatchResult from anime result.
        
        Args:
            item: Jikan API response item
            query: Original search query
            
        Returns:
            MatchResult or None if invalid
        """
        try:
            title = item.get("title", "")
            if not title:
                return None

            parsed = AdvancedMatcher().parse_filename(query) or {}
            
            # Try alternative titles for better matching
            alternative_titles = []
            if "title_english" in item:
                alternative_titles.append(item["title_english"])
            if "title_japanese" in item:
                alternative_titles.append(item["title_japanese"])
            
            # Add synonyms if available
            for synonym in item.get("title_synonyms", []):
                if synonym:
                    alternative_titles.append(synonym)
            
            year = None
            aired = item.get("aired", {})
            if aired and aired.get("from"):
                try:
                    year = int(aired["from"][:4])
                except (ValueError, TypeError):
                    pass
            if parsed.get("year") and not year:
                year = parsed.get("year")
            season = parsed.get("season")
            episode = parsed.get("episode")
            
            # Calculate confidence
            scorer = ConfidenceScorer()
            
            # Try matching against all available titles
            all_titles = [title] + alternative_titles
            best_match = max([fuzzy_match(t, query) for t in all_titles if t] or [0])
            
            confidence = scorer.calculate(
                title_match=best_match > 0.95,
                title_fuzzy_ratio=best_match if best_match <= 0.95 else None,
                season_match=season is not None,
                episode_match=episode is not None,
                year_match=(year is not None),
                has_episode_info=episode is not None
            )
            
            return MatchResult(
                source_path=Path(query),
                filename=query,
                provider=MatchProvider.MAL,
                confidence=confidence,
                title=title,
                series_name=title,
                season=season,
                episode=episode,
                year=year
            )
        except Exception:
            return None
