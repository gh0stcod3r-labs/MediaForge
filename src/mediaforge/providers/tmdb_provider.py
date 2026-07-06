"""TMDB provider for movie and TV show metadata."""

import requests
from typing import Optional, List
from pathlib import Path

from . import BaseProvider, ProviderStatus, ProviderResponse
from ..match_result import MatchResult, MatchProvider
from ..cache import get_cache
from ..matcher import AdvancedMatcher
from .scoring import ConfidenceScorer, fuzzy_match
from ..config import get_settings


TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_REQUEST_TIMEOUT = 5


class TMDBProvider(BaseProvider):
    """TMDB provider for TV shows and movies."""

    api_base = TMDB_API_BASE  # exposed for centralized provider-lookup logging
    
    @property
    def provider_name(self) -> str:
        """Provider name."""
        return "TMDB"
    
    @property
    def requires_api_key(self) -> bool:
        """TMDB requires an API key."""
        return True
    
    def test_connection(self) -> bool:
        """Test TMDB API connection with current API key.
        
        Returns:
            True if API key is valid, False otherwise
        """
        api_key = get_settings().get_api_key("tmdb")
        if not api_key:
            return False
        
        try:
            response = requests.get(
                f"{TMDB_API_BASE}/configuration",
                params={"api_key": api_key},
                timeout=TMDB_REQUEST_TIMEOUT
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def search(self, query: str, source_path: Optional[Path] = None) -> ProviderResponse:
        """Search for TV shows or movies.
        
        Args:
            query: Search query (title or filename)
            source_path: Source file path (for MatchResult)
            
        Returns:
            ProviderResponse with matches or error
        """
        api_key = get_settings().get_api_key("tmdb")
        if not api_key:
            return ProviderResponse(
                status=ProviderStatus.INVALID_KEY,
                error_message="TMDB API key not configured"
            )
        
        # Check cache first
        cache = get_cache()
        cached = cache.get("TMDB", query)
        if cached:
            return ProviderResponse(
                status=ProviderStatus.OK,
                matches=cached.get("matches", [])
            )
        
        try:
            # Try TV search first, then movie
            tv_results = self._search_tv(query, api_key)
            movie_results = self._search_movies(query, api_key)
            
            # Combine results, TV first (most likely for media organization)
            all_results = tv_results + movie_results
            
            if not all_results:
                return ProviderResponse(
                    status=ProviderStatus.NOT_FOUND,
                    error_message=f"No results found for: {query}"
                )
            
            matches = [result for result in all_results if result is not None]
            
            # Cache results
            if matches:
                cache.set("TMDB", query, {"matches": matches})
            
            return ProviderResponse(
                status=ProviderStatus.OK,
                matches=matches
            )
        
        except requests.Timeout:
            return ProviderResponse(
                status=ProviderStatus.TIMEOUT,
                error_message=f"TMDB request timed out after {TMDB_REQUEST_TIMEOUT}s"
            )
        except requests.exceptions.ConnectionError:
            return ProviderResponse(
                status=ProviderStatus.NO_INTERNET,
                error_message="No internet connection available"
            )
        except Exception as e:
            return ProviderResponse(
                status=ProviderStatus.ERROR,
                error_message=f"TMDB API error: {str(e)}"
            )
    
    def _search_tv(self, query: str, api_key: str) -> List[Optional[MatchResult]]:
        """Search for TV shows.
        
        Args:
            query: Search query
            api_key: TMDB API key
            
        Returns:
            List of MatchResult objects
        """
        try:
            response = requests.get(
                f"{TMDB_API_BASE}/search/tv",
                params={"api_key": api_key, "query": query},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", [])[:5]:  # Top 5 results
                match = self._build_tv_match(item, query)
                if match:
                    results.append(match)
            
            return results
        except Exception:
            return []
    
    def _search_movies(self, query: str, api_key: str) -> List[Optional[MatchResult]]:
        """Search for movies.
        
        Args:
            query: Search query
            api_key: TMDB API key
            
        Returns:
            List of MatchResult objects
        """
        try:
            response = requests.get(
                f"{TMDB_API_BASE}/search/movie",
                params={"api_key": api_key, "query": query},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", [])[:5]:  # Top 5 results
                match = self._build_movie_match(item, query)
                if match:
                    results.append(match)
            
            return results
        except Exception:
            return []
    
    def _build_tv_match(self, item: dict, query: str) -> Optional[MatchResult]:
        """Build MatchResult from TV show result.
        
        Args:
            item: TMDB API response item
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
            first_air = item.get("first_air_date", "")
            if first_air:
                year = int(first_air[:4])
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
                provider=MatchProvider.TMDB,
                confidence=confidence,
                title=title,
                series_name=title,
                season=season,
                episode=episode,
                episode_title=parsed.get("episode_title"),
                year=year
            )
        except Exception:
            return None
    
    def _build_movie_match(self, item: dict, query: str) -> Optional[MatchResult]:
        """Build MatchResult from movie result.
        
        Args:
            item: TMDB API response item
            query: Original search query
            
        Returns:
            MatchResult or None if invalid
        """
        try:
            title = item.get("title", "")
            if not title:
                return None

            parsed = AdvancedMatcher().parse_filename(query) or {}
            
            year = None
            release_date = item.get("release_date", "")
            if release_date:
                year = int(release_date[:4])
            if parsed.get("year") and not year:
                year = parsed.get("year")
            
            # Calculate confidence
            scorer = ConfidenceScorer()
            title_match = fuzzy_match(title, query)
            confidence = scorer.calculate(
                title_match=title_match > 0.95,
                title_fuzzy_ratio=title_match if title_match <= 0.95 else None,
                year_match=(year is not None)
            )
            
            return MatchResult(
                source_path=Path(query),
                filename=query,
                provider=MatchProvider.TMDB,
                confidence=confidence,
                title=title,
                series_name=title,
                year=year
            )
        except Exception:
            return None
