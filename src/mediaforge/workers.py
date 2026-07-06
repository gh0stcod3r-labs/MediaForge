"""Background workers for batch matching and file operations."""

from __future__ import annotations

from typing import List, Optional
import threading

from PySide6.QtCore import QObject, Signal, Slot

from .async_matcher import AsyncMatcher
from .providers.provider_selector import ProviderSelector
from .rename_engine import RenameEngine
from .operation_result import OperationPlan


class MatchWorker(QObject):
    """Run matching off the UI thread."""

    progress = Signal(int, int, str)
    finished = Signal(list, list, int)
    failed = Signal(str, str)

    def __init__(
        self,
        filenames: List[str],
        selector: ProviderSelector,
        matcher: AsyncMatcher,
        selected_provider: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.filenames = filenames
        self.selector = selector
        self.matcher = matcher
        self.selected_provider = selected_provider
        self._cancel_event = threading.Event()

    @Slot()
    def run(self) -> None:
        try:
            results, attempts, completed = self.matcher.match_batch_with_progress(
                filenames=self.filenames,
                selector=self.selector,
                progress_callback=self._on_progress,
                selected_provider=self.selected_provider,
            )
            self.finished.emit(results, attempts, completed)
        except Exception as exc:
            self.failed.emit(type(exc).__name__, str(exc))

    @Slot()
    def cancel(self) -> None:
        self._cancel_event.set()
        self.matcher.cancel()

    def _on_progress(self, current: int, total: int, filename: str) -> None:
        self.progress.emit(current, total, filename)


class OperationWorker(QObject):
    """Run file operations off the UI thread."""

    progress = Signal(dict)
    finished = Signal(object)
    failed = Signal(str, str)

    def __init__(self, engine: RenameEngine, plan: OperationPlan, verify_after_copy: bool = True) -> None:
        super().__init__()
        self.engine = engine
        self.plan = plan
        self.verify_after_copy = verify_after_copy
        self._cancel_event = threading.Event()

    @Slot()
    def run(self) -> None:
        try:
            self.engine.set_progress_callback(self._on_progress)
            result = self.engine.execute_plan(
                self.plan,
                verify_after_copy=self.verify_after_copy,
                cancel_event=self._cancel_event,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(type(exc).__name__, str(exc))

    @Slot()
    def cancel(self) -> None:
        self._cancel_event.set()

    def _on_progress(self, payload: dict) -> None:
        self.progress.emit(payload)
