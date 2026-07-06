"""Core file operations engine for MediaForge Organizer."""

import logging
import re
import shutil
from pathlib import Path
from typing import Optional, List, Callable
import time

from .match_result import MatchResult
from .operation_result import (
    OperationResult, OperationPlan, ExecutionResult,
    OperationType, OperationStatus
)
from .models import MediaType
from .logger import OperationLogger


class RenameEngine:
    """Core file operations engine. Only class allowed to modify files."""
    
    def __init__(self, logger: Optional[OperationLogger] = None):
        """Initialize rename engine with optional logger."""
        self.logger = logger or OperationLogger()
        self.progress_callback: Optional[Callable] = None
        self.log = logging.getLogger(__name__)
    
    def set_progress_callback(self, callback: Callable[[dict], None]) -> None:
        """Set callback for progress updates."""
        self.progress_callback = callback
    
    def plan_operations(
        self,
        matches: List[MatchResult],
        media_type: MediaType,
        destination_root: Path,
        operation_type: str = "rename_copy",
        is_dry_run: bool = False,
    ) -> OperationPlan:
        """
        Generate a plan of operations before execution.
        
        operation_type: "rename_move", "rename_copy", "rename_only", "folders_only"
        """
        plan = OperationPlan(is_dry_run=is_dry_run)

        created_folders = set()

        for match in matches:
            # Generate destination path
            dest_path = self.build_destination_path(match, destination_root)
            
            if dest_path is None:
                plan.add_warning(f"Could not determine destination for {match.filename}")
                continue
            
            # Ensure parent folder is in plan
            parent_folder = dest_path.parent
            if parent_folder not in created_folders:
                plan.folders_to_create.append(parent_folder)
                created_folders.add(parent_folder)
            
            # Create operations based on type
            if operation_type == "folders_only":
                # Only folder creation
                pass  # Folders already added above
            
            elif operation_type == "rename_only":
                # Rename in source location
                dest_in_source = match.source_path.parent / dest_path.name
                op = OperationResult(
                    operation_type=OperationType.RENAME,
                    source_path=match.source_path,
                    destination_path=dest_in_source,
                    status=OperationStatus.SUCCESS,
                    provider=match.provider.value,
                    confidence=match.confidence,
                )
                plan.add_operation(op)
            
            elif operation_type == "rename_copy":
                op = OperationResult(
                    operation_type=OperationType.COPY,
                    source_path=match.source_path,
                    destination_path=dest_path,
                    status=OperationStatus.SUCCESS,
                    provider=match.provider.value,
                    confidence=match.confidence,
                )
                plan.add_operation(op)
            
            elif operation_type == "rename_move":
                op = OperationResult(
                    operation_type=OperationType.MOVE,
                    source_path=match.source_path,
                    destination_path=dest_path,
                    status=OperationStatus.SUCCESS,
                    provider=match.provider.value,
                    confidence=match.confidence,
                )
                plan.add_operation(op)
            
            plan.total_files += 1
            
            # Get file size safely
            try:
                if match.source_path.exists():
                    plan.total_size_bytes += match.source_path.stat().st_size
            except Exception:
                pass
        
        # Pre-execution validation
        self._validate_plan(plan)
        
        return plan
    
    def execute_plan(
        self,
        plan: OperationPlan,
        verify_after_copy: bool = False,
        cancel_event=None,
    ) -> ExecutionResult:
        """Execute a planned set of operations."""
        result = ExecutionResult()
        start_time = time.time()
        
        # Create folder structure
        if plan.folders_to_create and not plan.is_dry_run:
            for folder in plan.folders_to_create:
                try:
                    folder.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    plan.add_warning(f"Failed to create folder {folder}: {str(e)}")
        
        # Execute each operation
        for idx, op in enumerate(plan.operations):
            if cancel_event is not None and cancel_event.is_set():
                op.status = OperationStatus.SKIPPED
                result.skipped.append(op)
                continue

            self._update_progress(idx, len(plan.operations), op.source_path.name)
            
            try:
                if plan.is_dry_run:
                    # Dry run: validate without executing
                    self._validate_operation(op)
                    result.skipped.append(op)
                
                elif op.operation_type == OperationType.COPY:
                    self._execute_copy(op, verify_after_copy, result)
                
                elif op.operation_type == OperationType.MOVE:
                    self._execute_move(op, result)
                
                elif op.operation_type == OperationType.RENAME:
                    self._execute_rename(op, result)
            
            except Exception as e:
                op.status = OperationStatus.FAILED
                op.error_message = str(e)
                result.failed.append(op)
                self.logger.log_operation(op)
        
        result.total_duration_ms = (time.time() - start_time) * 1000
        
        # Push successful operations to undo stack (batch-wise)
        if result.successful and not plan.is_dry_run:
            self.logger.push_undo_batch(result.successful)
        
        return result
    
    def build_destination_path(
        self,
        match: MatchResult,
        destination_root: Path,
    ) -> Optional[Path]:
        """Build the final destination path from match metadata."""
        self.prepare_match_metadata(match)
        series_name = self._sanitize_path_part(match.series_name or "Unknown")
        season_folder = f"Season {match.season:02d}" if match.season else None
        filename = match.proposed_filename or self._build_proposed_filename(match)

        if not filename:
            return None

        base = destination_root / series_name
        if season_folder:
            return base / season_folder / filename
        return base / filename

    def _build_proposed_filename(self, match: MatchResult) -> str:
        """Build a user-facing proposed filename from metadata."""
        stem_parts = [self.normalize_series_name(match)]

        if match.season is not None and match.episode is not None:
            stem_parts.append(f"S{match.season:02d}E{match.episode:02d}")

        episode_title = self.normalize_episode_title(match)
        if episode_title:
            match.episode_title = episode_title
            stem_parts.append(match.episode_title)
        elif match.year:
            stem_parts.append(str(match.year))

        safe_stem = " - ".join(part for part in stem_parts if part)
        safe_stem = self._sanitize_path_part(safe_stem)
        return f"{safe_stem}{match.source_path.suffix}"

    def prepare_match_metadata(self, match: MatchResult) -> None:
        """Normalize and populate destination-related metadata on a match."""
        match.series_name = self.normalize_series_name(match)
        if match.episode is not None and match.season is None:
            match.season = 1
        if not match.episode_title:
            match.episode_title = self.normalize_episode_title(match)
        if not match.proposed_filename:
            match.proposed_filename = self._build_proposed_filename(match)

    def normalize_series_name(self, match_result: MatchResult) -> str:
        """Normalize series name for folder generation."""
        source_name = Path(match_result.filename).stem if match_result.filename else ""
        candidate = (match_result.series_name or match_result.title or source_name or "Unknown")
        cleaned = candidate.replace(".", " ").replace("_", " ")

        # Parse potential series base from filename markers.
        filename_base = ""
        marker_match = re.match(
            r"^(?P<series>.*?)(?:\s*[\]\)\-:]*\s*)(?:episode\s*\d{1,3}|s\d{1,2}e\d{1,3}|\d{1,2}x\d{1,3}|\d{1,3})(?:\s*-\s*.*)?$",
            source_name.replace(".", " ").replace("_", " "),
            flags=re.IGNORECASE,
        )
        if marker_match and marker_match.group("series").strip():
            filename_base = marker_match.group("series").strip()

        if filename_base and filename_base.lower() in cleaned.lower():
            cleaned = filename_base
        else:
            marker_match = re.match(
                r"^(?P<series>.*?)(?:\s*[\]\)\-:]*\s*)(?:episode\s*\d{1,3}|s\d{1,2}e\d{1,3}|\d{1,2}x\d{1,3}|\d{1,3})(?:\s*-\s*.*)?$",
                cleaned,
                flags=re.IGNORECASE,
            )
            if marker_match and marker_match.group("series").strip():
                cleaned = marker_match.group("series")
            else:
                cleaned = re.split(r"\bS\d{1,2}E\d{1,3}\b", cleaned, flags=re.IGNORECASE)[0]

        # Remove known release/codec tags and bracket junk.
        cleaned = re.sub(r"\b(720p|1080p|2160p|4k|x264|x265|hevc|aac|flac|webrip|bdrip|bluray|dvdrip)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[\[\]\{\}\(\)]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -._")

        if not cleaned:
            cleaned = match_result.series_name or match_result.title or "Unknown"
        return self._sanitize_path_part(self._to_title_case(cleaned))

    def normalize_episode_title(self, match_result: MatchResult) -> Optional[str]:
        """Normalize episode title for filename usage only.

        Strips season/episode markers (S01E01, 1x01, "Episode 3", etc.)
        regardless of whether the raw value came from a fresh filename
        parse or was already set on the match - a pre-set episode_title
        is not assumed to be clean. Without this, any upstream path that
        sets episode_title to something like "S01E01 - Meeting of Fate"
        would be passed straight through unstripped and duplicate the
        season/episode tag already inserted by _build_proposed_filename.
        """
        if match_result.episode_title:
            raw = match_result.episode_title
        else:
            stem = Path(match_result.filename).stem if match_result.filename else ""
            title_match = re.search(
                r"(?:s\d{1,2}e\d{1,3}|\d{1,2}x\d{1,3}|episode\s*\d{1,3}|\b\d{1,3}\b)\s*-\s*(?P<title>.+)$",
                stem,
                flags=re.IGNORECASE,
            )
            raw = title_match.group("title") if title_match else ""

        # Strip a leading "<marker> - " prefix if the pre-set episode_title
        # still has one (defends against any upstream path that sets
        # episode_title to something like "S01E01 - Meeting of Fate"
        # instead of the isolated title).
        title_match = re.search(
            r"(?:s\d{1,2}e\d{1,3}|\d{1,2}x\d{1,3}|episode\s*\d{1,3}|\b\d{1,3}\b)\s*-\s*(?P<title>.+)$",
            raw,
            flags=re.IGNORECASE,
        )
        if title_match:
            raw = title_match.group("title")

        # Defensively remove any remaining bare season/episode markers
        # even without a " - " separator (e.g. a duplicated marker).
        raw = re.sub(r"\bs\d{1,2}e\d{1,3}\b", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\b\d{1,2}x\d{1,3}\b", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\bepisode\s*\d{1,3}\b", "", raw, flags=re.IGNORECASE)

        raw = re.sub(r"\b(720p|1080p|2160p|4k|x264|x265|hevc|aac|flac|webrip|bdrip|bluray|dvdrip)\b", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"[\[\]\{\}\(\)]", " ", raw)
        raw = re.sub(r"\s+", " ", raw).strip(" -._")
        if not raw:
            return None
        return self._sanitize_path_part(self._to_title_case(raw))

    @staticmethod
    def _sanitize_path_part(value: str) -> str:
        """Remove invalid path characters."""
        invalid = '<>:"/\\|?*'
        for char in invalid:
            value = value.replace(char, "")
        return value.strip(" .")

    def _log_destination_debug(self, op: OperationResult) -> None:
        """Log normalized destination metadata before file operations."""
        filename = op.destination_path.name
        destination_folder = str(op.destination_path.parent)
        season = ""
        series_name = op.destination_path.parent.name
        if op.destination_path.parent.name.lower().startswith("season "):
            season = op.destination_path.parent.name
            series_name = op.destination_path.parent.parent.name

        ep_match = re.search(r"S(?P<season>\d{2})E(?P<episode>\d{2,3})", filename, flags=re.IGNORECASE)
        episode = ep_match.group("episode") if ep_match else ""
        episode_title = ""
        title_match = re.match(r".*?-\s*S\d{2}E\d{2,3}\s*-\s*(?P<title>.+?)\.[^.]+$", filename, flags=re.IGNORECASE)
        if title_match:
            episode_title = title_match.group("title")

        self.log.info(
            "series_name=%s season=%s episode=%s episode_title=%s destination_folder=%s final_filename=%s",
            series_name,
            season,
            episode,
            episode_title,
            destination_folder,
            filename,
        )

    @staticmethod
    def _to_title_case(value: str) -> str:
        """Title-case with common short words kept lowercase."""
        small_words = {"of", "and", "the", "a", "an", "in", "on", "to"}
        upper_words = {"vs"}
        words = value.split()
        if not words:
            return value

        def normalize_word(word: str, is_first: bool) -> str:
            lower = word.lower()
            if lower in upper_words:
                return lower.upper()
            if not is_first and lower in small_words:
                return lower
            return word.capitalize()

        normalized = [normalize_word(words[0], is_first=True)]
        normalized.extend(normalize_word(w, is_first=False) for w in words[1:])
        return " ".join(normalized)
    
    def _execute_copy(
        self,
        op: OperationResult,
        verify: bool,
        result: ExecutionResult,
    ) -> None:
        """Execute copy operation."""
        start = time.time()
        
        # Check source
        if not op.source_path.exists():
            raise FileNotFoundError(f"Source not found: {op.source_path}")
        
        # Handle duplicates
        dest = self._handle_duplicate(op.destination_path)
        op.destination_path = dest
        
        # Ensure parent exists
        op.destination_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._log_destination_debug(op)

        # Copy
        self.log.info("Copy start: %s -> %s", op.source_path, op.destination_path)
        shutil.copy2(op.source_path, op.destination_path)
        
        # Verify if requested
        if verify:
            if not self._verify_copy(op.source_path, op.destination_path):
                raise IOError("Copy verification failed")
        
        op.status = OperationStatus.SUCCESS
        op.duration_ms = (time.time() - start) * 1000
        self.log.info("Copy end: %s -> %s", op.source_path, op.destination_path)
        result.successful.append(op)
        self.logger.log_operation(op)
    
    def _execute_move(
        self,
        op: OperationResult,
        result: ExecutionResult,
    ) -> None:
        """Execute move operation."""
        start = time.time()
        
        # Check source
        if not op.source_path.exists():
            raise FileNotFoundError(f"Source not found: {op.source_path}")
        
        # Handle duplicates
        dest = self._handle_duplicate(op.destination_path)
        op.destination_path = dest
        
        # Ensure parent exists
        op.destination_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._log_destination_debug(op)

        # Move
        self.log.info("Move start: %s -> %s", op.source_path, op.destination_path)
        shutil.move(str(op.source_path), str(op.destination_path))
        
        op.status = OperationStatus.SUCCESS
        op.duration_ms = (time.time() - start) * 1000
        self.log.info("Move end: %s -> %s", op.source_path, op.destination_path)
        result.successful.append(op)
        self.logger.log_operation(op)
    
    def _execute_rename(
        self,
        op: OperationResult,
        result: ExecutionResult,
    ) -> None:
        """Execute rename operation (in-place)."""
        start = time.time()
        
        # Check source
        if not op.source_path.exists():
            raise FileNotFoundError(f"Source not found: {op.source_path}")
        
        # Handle duplicates
        dest = self._handle_duplicate(op.destination_path)
        op.destination_path = dest
        
        self._log_destination_debug(op)

        # Rename
        self.log.info("Rename start: %s -> %s", op.source_path, op.destination_path)
        op.source_path.rename(op.destination_path)
        
        op.status = OperationStatus.SUCCESS
        op.duration_ms = (time.time() - start) * 1000
        self.log.info("Rename end: %s -> %s", op.source_path, op.destination_path)
        result.successful.append(op)
        self.logger.log_operation(op)
    
    def _handle_duplicate(self, dest_path: Path) -> Path:
        """Handle duplicate destination path."""
        if not dest_path.exists():
            return dest_path
        
        # Append counter
        stem = dest_path.stem
        suffix = dest_path.suffix
        parent = dest_path.parent
        counter = 1
        
        while True:
            new_name = f"{stem} ({counter}){suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
    
    def _verify_copy(self, source: Path, dest: Path) -> bool:
        """Verify copy by comparing file sizes."""
        try:
            source_size = source.stat().st_size
            dest_size = dest.stat().st_size
            return source_size == dest_size
        except Exception:
            return False
    
    def _validate_operation(self, op: OperationResult) -> None:
        """Validate operation before execution."""
        if not op.source_path.exists():
            raise FileNotFoundError(f"Source not found: {op.source_path}")
        
        # Check parent destination exists (will be created)
        # Check permissions (basic)
    
    def _validate_plan(self, plan: OperationPlan) -> None:
        """Validate entire plan."""
        # Check total size
        available_space = self._get_available_space(plan.folders_to_create[0] if plan.folders_to_create else Path.home())
        if plan.total_size_bytes > available_space:
            plan.add_warning(f"Insufficient disk space: {plan.total_size_bytes / 1024 / 1024:.1f}MB required")
    
    @staticmethod
    def _get_available_space(path: Path) -> int:
        """Get available disk space in bytes (cross-platform)."""
        try:
            usage = shutil.disk_usage(str(path))
            return usage.free
        except Exception:
            return float('inf')  # Return unlimited if we can't check
    
    def _update_progress(self, current: int, total: int, current_file: str) -> None:
        """Update progress callback."""
        if self.progress_callback:
            self.progress_callback({
                "current": current + 1,
                "total": total,
                "current_file": current_file,
                "percentage": int((current + 1) / total * 100) if total > 0 else 0,
            })
