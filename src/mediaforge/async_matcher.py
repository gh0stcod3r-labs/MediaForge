"""Async/parallel provider matching for Phase 3 performance."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED, Future
from typing import List, Tuple, Optional, Dict
from pathlib import Path
from queue import Queue

from .providers.provider_selector import ProviderSelector
from .match_result import MatchResult


class AsyncMatcher:
    """Parallel provider lookup with rate limiting and cancellation."""
    
    def __init__(self, max_workers: int = 3, timeout: int = 10):
        """Initialize async matcher.
        
        Args:
            max_workers: Maximum concurrent provider calls
            timeout: Individual request timeout in seconds
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cancel_flag = threading.Event()
        self._progress_queue: Queue = Queue()
        self._results_lock = threading.Lock()
    
    def match_batch(self, filenames: List[str], 
                    selector: Optional[ProviderSelector] = None,
                    selected_provider: Optional[str] = None) -> Tuple[List[Optional[MatchResult]], List[Dict], int]:
        """Match files in parallel with order preservation.
        
        Args:
            filenames: List of filenames to match
            selector: ProviderSelector instance (creates new if None)
            
        Returns:
            Tuple of (results preserving order, per-file attempt info, files_completed).
            attempt info is a dict per file: {"provider": str, "status": str, "error": Optional[str]}
            so callers can tell a genuine automatic-fallback Offline match apart from a
            failed TMDB/AniList/MAL/TVMaze lookup, instead of both looking identical.
        """
        if selector is None:
            selector = ProviderSelector()
        
        # Reset cancellation flag
        self._cancel_flag.clear()
        
        futures_map: Dict[Future, int] = {}
        submitted_at: Dict[Future, float] = {}
        results: List[Optional[MatchResult]] = [None] * len(filenames)
        attempts: List[Dict] = [{"provider": None, "status": "not_attempted", "error": None}] * len(filenames)

        for index, filename in enumerate(filenames):
            if self._cancel_flag.is_set():
                break

            future = self.executor.submit(
                selector.search_with_fallback,
                filename,
                Path(filename),
                selected_provider,
            )
            futures_map[future] = index
            submitted_at[future] = time.monotonic()

        pending = set(futures_map.keys())
        completed_count = 0
        while pending and not self._cancel_flag.is_set():
            done, pending = wait(pending, timeout=0.1, return_when=FIRST_COMPLETED)

            for future in done:
                index = futures_map[future]
                try:
                    response, provider_name = future.result()
                    attempts[index] = {
                        "provider": provider_name,
                        "status": response.status.value,
                        "error": response.error_message,
                    }
                    if response.matches:
                        results[index] = response.matches[0]
                except Exception as e:
                    print(f"Error matching {filenames[index]}: {e}")
                    attempts[index] = {"provider": None, "status": "exception", "error": str(e)}
                completed_count += 1

            now = time.monotonic()
            timed_out = [future for future in list(pending) if now - submitted_at[future] > self.timeout]
            for future in timed_out:
                index = futures_map[future]
                future.cancel()
                pending.discard(future)
                attempts[index] = {"provider": None, "status": "timeout", "error": f"Timed out after {self.timeout}s"}
                completed_count += 1
                print(f"Timed out matching {filenames[index]}")

        return results, attempts, completed_count
    
    def match_batch_with_progress(self, filenames: List[str],
                                  selector: Optional[ProviderSelector] = None,
                                  progress_callback=None,
                                  selected_provider: Optional[str] = None) -> Tuple[List[Optional[MatchResult]], List[Dict], int]:
        """Match files in parallel with progress reporting.
        
        Args:
            filenames: List of filenames to match
            selector: ProviderSelector instance
            progress_callback: Function(current_index, total) for progress updates
            
        Returns:
            Tuple of (results, per-file attempt info, completed_count).
            attempt info is a dict per file: {"provider": str, "status": str, "error": Optional[str]}
        """
        if selector is None:
            selector = ProviderSelector()
        
        self._cancel_flag.clear()
        
        futures_map: Dict[Future, int] = {}
        submitted_at: Dict[Future, float] = {}
        results: List[Optional[MatchResult]] = [None] * len(filenames)
        attempts: List[Dict] = [{"provider": None, "status": "not_attempted", "error": None}] * len(filenames)
        completed_count = 0
        
        # Submit tasks
        for index, filename in enumerate(filenames):
            if self._cancel_flag.is_set():
                break
            
            future = self.executor.submit(
                selector.search_with_fallback,
                filename,
                Path(filename),
                selected_provider,
            )
            futures_map[future] = index
            submitted_at[future] = time.monotonic()
            
            if progress_callback:
                progress_callback(index + 1, len(filenames), "queued")

        pending = set(futures_map.keys())
        while pending and not self._cancel_flag.is_set():
            done, pending = wait(pending, timeout=0.1, return_when=FIRST_COMPLETED)

            for future in done:
                index = futures_map[future]
                filename = filenames[index]
                try:
                    response, provider_name = future.result()
                    attempts[index] = {
                        "provider": provider_name,
                        "status": response.status.value,
                        "error": response.error_message,
                    }
                    if response.matches:
                        results[index] = response.matches[0]
                except Exception as e:
                    print(f"Error matching {filename}: {e}")
                    attempts[index] = {"provider": None, "status": "exception", "error": str(e)}
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count, len(filenames), filename)

            now = time.monotonic()
            timed_out = [future for future in list(pending) if now - submitted_at[future] > self.timeout]
            for future in timed_out:
                index = futures_map[future]
                filename = filenames[index]
                future.cancel()
                pending.discard(future)
                attempts[index] = {"provider": None, "status": "timeout", "error": f"Timed out after {self.timeout}s"}
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count, len(filenames), f"timeout: {filename}")

        return results, attempts, completed_count
    
    def cancel(self) -> None:
        """Signal cancellation."""
        self._cancel_flag.set()
    
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancel_flag.is_set()
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor.
        
        Args:
            wait: Wait for pending tasks to complete
        """
        if wait:
            self.executor.shutdown(wait=True)
        else:
            self.executor.shutdown(wait=False)
    
    def reset(self) -> None:
        """Reset for new batch."""
        self._cancel_flag.clear()


class BatchMatchResult:
    """Statistics for a batch matching operation."""
    
    def __init__(self):
        """Initialize batch result."""
        self.files_scanned = 0
        self.files_matched = 0
        self.files_needs_review = 0
        self.files_no_match = 0
        
        self.provider_usage: Dict[str, int] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.api_failures = 0
        
        self.confidence_distribution: Dict[str, int] = {
            "0-50": 0,
            "50-80": 0,
            "80-100": 0
        }
        
        self.start_time = 0
        self.end_time = 0
    
    def add_result(self, match: MatchResult, provider: str) -> None:
        """Add result to batch stats.
        
        Args:
            match: Match result
            provider: Provider name
        """
        self.files_scanned += 1
        
        # Track provider usage
        self.provider_usage[provider] = self.provider_usage.get(provider, 0) + 1
        
        # Track confidence distribution
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
    
    def summary(self) -> str:
        """Generate text summary."""
        duration = self.end_time - self.start_time if self.end_time else 0
        
        summary = f"""
        Files Scanned: {self.files_scanned}
        Matched: {self.files_matched}
        Needs Review: {self.files_needs_review}
        No Match: {self.files_no_match}
        
        Providers Used: {", ".join(f"{p}:{c}" for p, c in self.provider_usage.items())}
        Cache: {self.cache_hits} hits, {self.cache_misses} misses
        API Failures: {self.api_failures}
        
        Confidence Distribution:
        80-100%: {self.confidence_distribution["80-100"]}
        50-80%: {self.confidence_distribution["50-80"]}
        0-50%: {self.confidence_distribution["0-50"]}
        
        Duration: {duration:.2f}s
        """
        
        return summary.strip()
