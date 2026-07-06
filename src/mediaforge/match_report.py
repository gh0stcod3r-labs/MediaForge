"""Match report generation for Phase 3 reporting."""

from dataclasses import dataclass, field
from typing import Dict, List
import time

from .match_result import MatchResult


@dataclass
class MatchReport:
    """Statistics and analysis for a batch matching operation."""
    
    files_scanned: int = 0
    files_matched: int = 0
    files_needs_review: int = 0
    files_no_match: int = 0
    
    provider_usage: Dict[str, int] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    api_failures: int = 0
    
    confidence_distribution: Dict[str, int] = field(default_factory=lambda: {
        "0-50": 0,
        "50-80": 0,
        "80-100": 0
    })
    
    estimated_folders_created: int = 0
    duplicate_detections: int = 0
    missing_episode_detections: int = 0
    
    start_time: float = 0
    end_time: float = 0
    error_count: int = 0
    
    def __post_init__(self):
        """Initialize timestamps if not set."""
        if self.start_time == 0:
            self.start_time = time.time()
    
    def add_match(self, match: MatchResult, provider: str) -> None:
        """Add a match result to report statistics.
        
        Args:
            match: MatchResult object
            provider: Name of provider that returned this match
        """
        self.files_scanned += 1
        
        # Track provider usage
        self.provider_usage[provider] = self.provider_usage.get(provider, 0) + 1
        
        # Track confidence distribution and categorize
        conf_pct = int(match.confidence * 100)
        
        if conf_pct < 50:
            self.confidence_distribution["0-50"] += 1
            self.files_no_match += 1
        elif conf_pct < 80:
            self.confidence_distribution["50-80"] += 1
            self.files_needs_review += 1
        else:
            self.confidence_distribution["80-100"] += 1
            self.files_matched += 1
    
    def get_duration(self) -> float:
        """Get operation duration in seconds."""
        if self.end_time == 0:
            return time.time() - self.start_time
        return self.end_time - self.start_time
    
    def finalize(self) -> None:
        """Mark operation as complete."""
        self.end_time = time.time()
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        duration = self.get_duration()
        
        summary_lines = [
            "=" * 50,
            "MATCH REPORT",
            "=" * 50,
            "",
            "Results:",
            f"  Matched:        {self.files_matched:,}",
            f"  Needs Review:   {self.files_needs_review:,}",
            f"  No Match:       {self.files_no_match:,}",
            f"  Total Scanned:  {self.files_scanned:,}",
            "",
            "Providers Used:",
        ]
        
        for provider, count in sorted(self.provider_usage.items(), key=lambda x: x[1], reverse=True):
            pct = (count / self.files_scanned * 100) if self.files_scanned > 0 else 0
            summary_lines.append(f"  {provider:.<15} {count:>4} ({pct:>5.1f}%)")
        
        summary_lines.extend([
            "",
            "Cache Performance:",
            f"  Hits:           {self.cache_hits:,}",
            f"  Misses:         {self.cache_misses:,}",
            f"  Hit Rate:       {self._hit_rate_pct():.1f}%",
            "",
            "Confidence Distribution:",
            f"  80-100%:        {self.confidence_distribution['80-100']:,}",
            f"  50-80%:         {self.confidence_distribution['50-80']:,}",
            f"  0-50%:          {self.confidence_distribution['0-50']:,}",
            "",
            "Statistics:",
            f"  API Failures:   {self.api_failures:,}",
            f"  Errors:         {self.error_count:,}",
            f"  Duration:       {duration:.2f}s",
            f"  Files/sec:      {self.files_scanned/duration if duration > 0 else 0:.1f}",
            "=" * 50,
        ])
        
        return "\n".join(summary_lines)
    
    def _hit_rate_pct(self) -> float:
        """Calculate cache hit rate percentage."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100
    
    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            "files_scanned": self.files_scanned,
            "files_matched": self.files_matched,
            "files_needs_review": self.files_needs_review,
            "files_no_match": self.files_no_match,
            "provider_usage": self.provider_usage,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate_pct": self._hit_rate_pct(),
            "api_failures": self.api_failures,
            "error_count": self.error_count,
            "confidence_distribution": self.confidence_distribution,
            "estimated_folders_created": self.estimated_folders_created,
            "duplicate_detections": self.duplicate_detections,
            "missing_episode_detections": self.missing_episode_detections,
            "duration_seconds": self.get_duration(),
            "files_per_second": self.files_scanned / self.get_duration() if self.get_duration() > 0 else 0,
        }
    
    def to_json_serializable(self) -> Dict:
        """Convert to JSON-serializable dictionary."""
        return self.to_dict()
    
    @staticmethod
    def from_matches(matches: List[tuple], provider_stats: Dict = None) -> "MatchReport":
        """Create report from list of matches.
        
        Args:
            matches: List of (MatchResult, provider_name) tuples
            provider_stats: Optional provider statistics dict
            
        Returns:
            MatchReport instance
        """
        report = MatchReport()
        
        for match, provider in matches:
            report.add_match(match, provider)
        
        if provider_stats:
            report.cache_hits = provider_stats.get("hits", 0)
            report.cache_misses = provider_stats.get("misses", 0)
            report.api_failures = provider_stats.get("failures", 0)
        
        report.finalize()
        return report
