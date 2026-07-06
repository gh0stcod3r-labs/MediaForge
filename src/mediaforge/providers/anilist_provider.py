"""AniList provider for anime metadata."""

import requests
from typing import Optional, List, Dict, Any
from pathlib import Path

from . import BaseProvider, ProviderStatus, ProviderResponse
from ..match_result import MatchResult, MatchProvider
from ..cache import get_cache
from ..matcher import AdvancedMatcher
from .scoring import ConfidenceScorer, fuzzy_match


ANILIST_API_URL = "https://graphql.anilist.co"
ANILIST_REQUEST_TIMEOUT = 5


class AniListProvider(BaseProvider):
    """AniList provider for anime metadata."""

    api_base = ANILIST_API_URL  # exposed for centralized provider-lookup logging
    
    @property
    def provider_name(self) -> str:
        return "AniList"
    
    @property
    def requires_api_key(self) -> bool:
        """AniList doesn't require an API key."""
        return False
    
    def test_connection(self) -> bool:
        """Test AniList API connection.
        
        AniList doesn't require authentication, so always return True if reachable.
        
        Returns:
            True if API is reachable
        """
        try:
            response = requests.post(
                ANILIST_API_URL,
                json={"query": "{ Page(page: 1, perPage: 1) { pageInfo { total } } }"},
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
        cached = cache.get("AniList", query)
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
            cache.set("AniList", query, {"matches": matches})
            
            return ProviderResponse(
                status=ProviderStatus.OK,
                matches=matches
            )
        
        except requests.Timeout:
            return ProviderResponse(
                status=ProviderStatus.TIMEOUT,
                error_message=f"AniList request timed out after {ANILIST_REQUEST_TIMEOUT}s"
            )
        except requests.exceptions.ConnectionError:
            return ProviderResponse(
                status=ProviderStatus.NO_INTERNET,
                error_message="No internet connection available"
            )
        except Exception as e:
            return ProviderResponse(
                status=ProviderStatus.ERROR,
                error_message=f"AniList API error: {str(e)}"
            )
    
    def _search_anime(self, query: str) -> List[Optional[MatchResult]]:
        """Search for anime using GraphQL.
        
        Args:
            query: Search query
            
        Returns:
            List of MatchResult objects
        """
        graphql_query = """
        query ($search: String) {
            Page(page: 1, perPage: 5) {
                media(search: $search, type: ANIME, sort: POPULARITY_DESC) {
                    id
                    title {
                        english
                        romaji
                        native
                    }
                    episodes
                    startDate {
                        year
                    }
                }
            }
        }
        """
        
        try:
            response = requests.post(
                ANILIST_API_URL,
                json={
                    "query": graphql_query,
                    "variables": {"search": query}
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                return []
            
            results = []
            for item in data.get("data", {}).get("Page", {}).get("media", []):
                match = self._build_anime_match(item, query)
                if match:
                    results.append(match)
            
            return results
        except Exception:
            return []
    
    def _build_anime_match(self, item: Dict[str, Any], query: str) -> Optional[MatchResult]:
        """Build MatchResult from anime result.
        
        Args:
            item: AniList API response item
            query: Original search query
            
        Returns:
            MatchResult or None if invalid
        """
        try:
            # Prefer English title, fall back to Romaji
            title_data = item.get("title", {})
            title = title_data.get("english") or title_data.get("romaji") or title_data.get("native")
            
            if not title:
                return None

            parsed = AdvancedMatcher().parse_filename(query) or {}
            
            year = None
            start_date = item.get("startDate", {})
            if start_date:
                year = start_date.get("year")
            if parsed.get("year") and not year:
                year = parsed.get("year")
            season = parsed.get("season")
            episode = parsed.get("episode")
            
            # Calculate confidence
            scorer = ConfidenceScorer()
            
            # Try matching against all title variants
            titles = [t for t in [
                title_data.get("english"),
                title_data.get("romaji"),
                title_data.get("native")
            ] if t]
            
            best_match = max([fuzzy_match(t, query) for t in titles] or [0])
            
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
                provider=MatchProvider.ANILIST,
                confidence=confidence,
                title=title,
                series_name=title,
                season=season,
                episode=episode,
                year=year
            )
        except Exception:
            return None
