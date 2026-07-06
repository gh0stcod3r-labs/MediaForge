"""Metadata cache system for MediaForge providers - Phase 3 enhanced."""

import json
import time
import hashlib
from pathlib import Path
from typing import Optional, Any, Dict, Tuple, List
from dataclasses import dataclass, asdict

from .match_result import MatchResult, MatchProvider


# Cache schema version for compatibility tracking
CACHE_SCHEMA_VERSION = 2


def _serialize_matches(matches: List[MatchResult]) -> List[Dict[str, Any]]:
    """Convert MatchResult objects into JSON-safe dicts.

    MatchResult carries a MatchProvider enum and several pathlib.Path
    fields, neither of which json.dump can serialize on its own. This
    was the root cause of provider results silently turning into
    'Offline' matches: cache.set() used to raise TypeError here, and
    the exception was swallowed by each provider's broad except block,
    converting a successful lookup into a generic error response.
    """
    serialized = []
    for m in matches:
        d = asdict(m)
        d["provider"] = m.provider.value
        d["source_path"] = str(m.source_path) if m.source_path else None
        d["destination_root"] = str(m.destination_root) if m.destination_root else None
        d["destination_path"] = str(m.destination_path) if m.destination_path else None
        serialized.append(d)
    return serialized


def _deserialize_matches(data: List[Dict[str, Any]]) -> List[MatchResult]:
    """Reconstruct MatchResult objects from cached JSON-safe dicts."""
    restored = []
    for raw in data:
        d = dict(raw)
        d["provider"] = MatchProvider(d["provider"])
        d["source_path"] = Path(d["source_path"]) if d.get("source_path") else None
        d["destination_root"] = Path(d["destination_root"]) if d.get("destination_root") else None
        d["destination_path"] = Path(d["destination_path"]) if d.get("destination_path") else None
        restored.append(MatchResult(**d))
    return restored


@dataclass
class CacheEntry:
    """Single cache entry with TTL and versioning."""
    provider: str
    query: str
    media_type: Optional[str] = None
    year: Optional[int] = None
    season: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    timestamp: float = 0
    ttl_seconds: int = 86400  # 24 hours default
    schema_version: int = CACHE_SCHEMA_VERSION
    provider_version: str = "1.0"


class MetadataCache:
    """Local cache for provider responses to reduce API calls."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache files. Defaults to ~/.mediaforge/cache/
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".mediaforge" / "cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.stats = {"hits": 0, "misses": 0, "corrupted": 0}
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for better matching.
        
        Args:
            query: Original query
            
        Returns:
            Normalized query
        """
        normalized = query.lower().strip()
        # Remove common filler
        for word in ["720p", "1080p", "4k", "hd", "sd", ".", "-", "_"]:
            normalized = normalized.replace(word, " ")
        
        # Collapse multiple spaces
        normalized = " ".join(normalized.split())
        return normalized
    
    def get_cache_key(self, provider: str, query: str, 
                      media_type: Optional[str] = None,
                      year: Optional[int] = None,
                      season: Optional[int] = None) -> str:
        """Create normalized, content-addressable cache key.
        
        Args:
            provider: Provider name
            query: Search query
            media_type: Media type (anime, tv, movie)
            year: Year (optional)
            season: Season number (optional)
            
        Returns:
            Cache key
        """
        normalized = self._normalize_query(query)
        key_parts = [provider, normalized, media_type or "unknown"]
        
        if year:
            key_parts.append(str(year))
        if season is not None:
            key_parts.append(f"s{season}")
        
        # Create deterministic hash of full key for filename safety
        full_key = "|".join(key_parts)
        key_hash = hashlib.md5(full_key.encode()).hexdigest()[:16]
        
        return f"{provider.lower()}_{key_hash}"
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """Get cache file path from cache key."""
        return self.cache_dir / f"{cache_key}.json"
    
    def get(self, provider: str, query: str,
            media_type: Optional[str] = None,
            year: Optional[int] = None,
            season: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get cached result if available and not expired.
        
        Args:
            provider: Provider name (TMDB, AniList, etc.)
            query: Search query
            media_type: Media type for better key matching
            year: Year for better key matching
            season: Season for better key matching
            
        Returns:
            Cached result dict if valid, None otherwise
        """
        cache_key = self.get_cache_key(provider, query, media_type, year, season)
        cache_file = self._get_cache_file(cache_key)
        
        if not cache_file.exists():
            self.stats["misses"] += 1
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            entry = CacheEntry(**data)
            
            # Check if expired
            age = time.time() - entry.timestamp
            if age > entry.ttl_seconds:
                cache_file.unlink()  # Delete expired cache
                self.stats["misses"] += 1
                return None
            
            # Check schema version for compatibility
            if entry.schema_version != CACHE_SCHEMA_VERSION:
                cache_file.unlink()  # Delete incompatible cache
                self.stats["misses"] += 1
                return None
            
            self.stats["hits"] += 1
            if entry.result and "matches" in entry.result and entry.result["matches"]:
                entry.result = dict(entry.result)
                entry.result["matches"] = _deserialize_matches(entry.result["matches"])
            return entry.result
        
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            # Corrupt cache file - mark and delete it
            self.stats["corrupted"] += 1
            try:
                cache_file.unlink()
            except OSError:
                pass
            self.stats["misses"] += 1
            return None
    
    def set(self, provider: str, query: str, result: Dict[str, Any],
            media_type: Optional[str] = None,
            year: Optional[int] = None,
            season: Optional[int] = None,
            ttl_seconds: int = 86400) -> None:
        """Cache a provider result.
        
        Args:
            provider: Provider name
            query: Search query
            result: Result to cache
            media_type: Media type for better key matching
            year: Year for better key matching
            season: Season for better key matching
            ttl_seconds: Time to live in seconds (default 24 hours)
        """
        cache_key = self.get_cache_key(provider, query, media_type, year, season)
        cache_file = self._get_cache_file(cache_key)

        result_to_store = result
        if isinstance(result, dict) and result.get("matches"):
            result_to_store = dict(result)
            result_to_store["matches"] = _serialize_matches(result["matches"])

        entry = CacheEntry(
            provider=provider,
            query=query,
            media_type=media_type,
            year=year,
            season=season,
            result=result_to_store,
            timestamp=time.time(),
            ttl_seconds=ttl_seconds,
            schema_version=CACHE_SCHEMA_VERSION
        )
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(asdict(entry), f, indent=2)
        except (OSError, TypeError) as e:
            print(f"Warning: Could not write cache: {e}")
    
    def clear(self, provider: Optional[str] = None) -> None:
        """Clear cache files.
        
        Args:
            provider: Clear only this provider's cache. If None, clear all.
        """
        if provider is None:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                except OSError:
                    pass
        else:
            prefix = provider.lower()
            for cache_file in self.cache_dir.glob(f"{prefix}_*.json"):
                try:
                    cache_file.unlink()
                except OSError:
                    pass
        
        self.stats = {"hits": 0, "misses": 0, "corrupted": 0}
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache hit/miss/corruption statistics."""
        return self.stats.copy()
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {"hits": 0, "misses": 0, "corrupted": 0}
    
    def get_cache_size(self) -> Tuple[int, int]:
        """Get cache size statistics.
        
        Returns:
            Tuple of (file_count, total_bytes)
        """
        total_files = 0
        total_bytes = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                total_files += 1
                total_bytes += cache_file.stat().st_size
            except OSError:
                pass
        
        return total_files, total_bytes
    
    def cleanup_corrupted(self) -> int:
        """Clean up corrupted cache files.
        
        Returns:
            Number of files deleted
        """
        deleted = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    json.load(f)
            except (json.JSONDecodeError, OSError):
                try:
                    cache_file.unlink()
                    deleted += 1
                except OSError:
                    pass
        
        return deleted


# Global cache instance
_cache_instance: Optional[MetadataCache] = None


def get_cache() -> MetadataCache:
    """Get or create global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MetadataCache()
    return _cache_instance
