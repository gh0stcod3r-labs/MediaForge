"""PySide6 UI application for MediaForge Organizer."""

import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QCheckBox, QMessageBox, QHeaderView, QProgressBar, QDialog,
    QGroupBox
)
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QFont, QColor
from . import __version__
from .models import MediaType
from .scanner import VideoScanner
from .parser import VideoParser
from .rename_engine import RenameEngine
from .match_result import MatchResult, MatchProvider
from .logger import OperationLogger
from .constants import (
    get_stylesheet, SPACING_MD, SPACING_XL, SPACING_LG, SPACING_SM,
    PRIMARY_TEXT, SECONDARY_TEXT, MUTED_TEXT, LIST_ITEM_FONT,
    LIST_PATH_FONT, ACCENT_SUCCESS, ACCENT_WARNING
)
# Phase 1 integration
from .config import get_settings
from .error_handler import ErrorHandler
from .dialogs import APIKeyDialog, ProgressDialog, ConfirmUndoDialog
from .matcher import AdvancedMatcher
from .providers.offline_provider import OfflineProvider

# Phase 3 integration
from .async_matcher import AsyncMatcher
from .cache import MetadataCache
from .match_report import MatchReport
from .providers.provider_selector import ProviderSelector
from .workers import MatchWorker, OperationWorker

# Configure debug logging
LOG_DIR = Path.home() / ".mediaforge" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_DIR / "debug.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MediaForgeApp(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        logger.info("=== MediaForge App Starting ===")
        logger.info("Entry point: src.main -> ModernMediaForgeWindow")
        logger.info("Active window class: %s", self.__class__.__name__)
        self.setWindowTitle("MediaForge Organizer")
        
        # Load settings first (will restore window geometry, theme, etc.)
        self.settings = get_settings()
        logger.info("Settings loaded")
        
        # Restore window geometry
        x, y, w, h = self.settings.get_window_geometry()
        self.setGeometry(x, y, w, h)
        
        # Apply theme from settings (persisted light/dark preference)
        self.theme = self.settings.get_theme() or "dark"
        self.setStyleSheet(get_stylesheet(self.theme))
        
        # Initialize core components
        self.scanner = VideoScanner()
        self.parser = VideoParser()
        self.logger = OperationLogger()
        self.engine = RenameEngine(self.logger)
        logger.info("Core components initialized")
        
        # Initialize providers and Phase 3 components
        self.offline_provider = OfflineProvider()
        self.current_provider = self.settings.get_provider() or "offline"
        
        # Phase 3 components (with safety flag for stability)
        self.use_async_matching = True  # Set to False if async causes issues
        try:
            self.cache = MetadataCache()
            self.provider_selector = ProviderSelector()
            self.async_matcher = AsyncMatcher(max_workers=3, timeout=10) if self.use_async_matching else None
            logger.info("Phase 3 components initialized (async_matching enabled)" if self.use_async_matching else "Phase 3 components initialized (async_matching disabled)")
        except Exception as e:
            logger.error(f"Phase 3 component init error: {e}")
            self.use_async_matching = False
            self.cache = None
            self.provider_selector = None
            self.async_matcher = None
        
        # UI state
        self.source_path = self.settings.get_last_source_path()
        self.output_path = self.settings.get_last_destination_root()
        self.selected_media_type = None
        self.current_plan = None
        self.current_matches = None
        self.progress_dialog = None
        self.operation_dialog = None
        self.match_report = None
        self.cache_stats = {"hits": 0, "misses": 0, "failures": 0}
        self.match_thread = None
        self.match_worker = None
        self.operation_thread = None
        self.operation_worker = None
        self._match_videos = []
        self._match_media_type = None
        self._match_selected_provider = None
        
        self._setup_ui()
        
        # Set up initial UI state from settings
        self._restore_ui_state()
        logger.info("UI setup complete")
    
    def closeEvent(self, event):
        """Save settings before closing."""
        self.settings.set_window_geometry(self.x(), self.y(), self.width(), self.height())
        self.settings.save()
        event.accept()
    
    def _restore_ui_state(self):
        """Restore UI state from settings."""
        # Restore paths if they exist
        if self.source_path and self.source_path.exists():
            self.source_path_label.setText(str(self.source_path))
        
        if self.output_path and self.output_path.exists():
            self.output_path_label.setText(str(self.output_path))
        
        # Restore provider selection if available
        if hasattr(self, 'provider_combo') and self.current_provider:
            provider_map = {
                "automatic": "Automatic",
                "offline": "Offline",
                "tmdb": "TMDB",
                "anilist": "AniList",
                "mal": "MyAnimeList",
                "myanimelist": "MyAnimeList",
                "tvmaze": "TVMaze",
            }
            display = provider_map.get(str(self.current_provider).lower(), str(self.current_provider))
            idx = self.provider_combo.findText(display)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
    
    def _setup_ui(self):
        """Set up the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_LG)
        layout.setContentsMargins(SPACING_XL, SPACING_XL, SPACING_XL, SPACING_XL)

        layout.addLayout(self._build_header())

        layout.addWidget(self._build_files_card())
        layout.addWidget(self._build_match_control_card())
        layout.addWidget(self._build_results_card(), stretch=1)

        central.setLayout(layout)

        # Setup status bar
        self._setup_status_bar()

    def _build_header(self) -> QHBoxLayout:
        """Build the top branding bar with app title and a theme toggle."""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(SPACING_SM)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = QLabel("MediaForge")
        title.setObjectName("appTitle")
        title_box.addWidget(title)
        subtitle = QLabel(f"Local-first media organizer  ·  v{__version__}")
        subtitle.setObjectName("appSubtitle")
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        self.theme_btn = QPushButton("☀ Light Mode" if self.theme == "dark" else "🌙 Dark Mode")
        self.theme_btn.setObjectName("secondaryButton")
        self.theme_btn.setMaximumWidth(150)
        self.theme_btn.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.theme_btn)

        return header_layout

    def _build_files_card(self) -> QGroupBox:
        """Build the source/output folder selection card."""
        card = QGroupBox("Source && Output")
        card_layout = QVBoxLayout()
        card_layout.setSpacing(SPACING_MD)

        # Source folder selection
        source_layout = QHBoxLayout()
        source_layout.setSpacing(SPACING_LG)
        source_label = QLabel("Source Folder:")
        source_label.setObjectName("secondary")
        source_label.setMinimumWidth(110)
        source_layout.addWidget(source_label)
        self.source_path_label = QLabel("Not selected")
        self.source_path_label.setObjectName("muted")
        source_layout.addWidget(self.source_path_label, stretch=1)
        source_btn = QPushButton("Browse...")
        source_btn.clicked.connect(self._select_source)
        source_btn.setMinimumWidth(120)
        source_layout.addWidget(source_btn)
        card_layout.addLayout(source_layout)

        # Output folder selection
        output_layout = QHBoxLayout()
        output_layout.setSpacing(SPACING_LG)
        output_label = QLabel("Output Folder:")
        output_label.setObjectName("secondary")
        output_label.setMinimumWidth(110)
        output_layout.addWidget(output_label)
        self.output_path_label = QLabel("Not selected")
        self.output_path_label.setObjectName("muted")
        output_layout.addWidget(self.output_path_label, stretch=1)
        output_btn = QPushButton("Browse...")
        output_btn.clicked.connect(self._select_output)
        output_btn.setMinimumWidth(120)
        output_layout.addWidget(output_btn)
        card_layout.addLayout(output_layout)

        card.setLayout(card_layout)
        return card

    def _build_match_control_card(self) -> QGroupBox:
        """Build the provider / category / options / scan card."""
        card = QGroupBox("Match Control")
        card_layout = QVBoxLayout()
        card_layout.setSpacing(SPACING_MD)

        # Provider + category on one row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(SPACING_LG)

        provider_label = QLabel("Provider:")
        provider_label.setObjectName("secondary")
        controls_layout.addWidget(provider_label)
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Automatic", "Offline", "TMDB", "AniList", "MyAnimeList", "TVMaze"])
        self.provider_combo.setMinimumWidth(150)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        controls_layout.addWidget(self.provider_combo)

        self.provider_key_btn = QPushButton("API Key")
        self.provider_key_btn.setObjectName("secondaryButton")
        self.provider_key_btn.clicked.connect(self._configure_api_key)
        self.provider_key_btn.setMaximumWidth(100)
        controls_layout.addWidget(self.provider_key_btn)

        controls_layout.addSpacing(SPACING_XL)

        media_label = QLabel("Category:")
        media_label.setObjectName("secondary")
        controls_layout.addWidget(media_label)
        self.media_combo = QComboBox()
        self.media_combo.addItems([mt.value for mt in MediaType])
        self.media_combo.setMinimumWidth(150)
        controls_layout.addWidget(self.media_combo)

        controls_layout.addStretch()
        card_layout.addLayout(controls_layout)

        # Options
        options_layout = QHBoxLayout()
        options_layout.setSpacing(SPACING_XL)
        self.copy_mode_check = QCheckBox("Copy mode (never deletes originals)")
        self.copy_mode_check.setChecked(True)
        options_layout.addWidget(self.copy_mode_check)
        self.dry_run_check = QCheckBox("Dry run (preview only)")
        options_layout.addWidget(self.dry_run_check)
        options_layout.addStretch()
        card_layout.addLayout(options_layout)

        # Scan button
        scan_layout = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Videos")
        self.scan_btn.clicked.connect(self._scan_videos)
        self.scan_btn.setMinimumWidth(150)
        scan_layout.addWidget(self.scan_btn)
        scan_layout.addStretch()
        card_layout.addLayout(scan_layout)

        card.setLayout(card_layout)
        return card

    def _build_results_card(self) -> QGroupBox:
        """Build the results table + export/action buttons card."""
        card = QGroupBox("Organization Plan")
        card_layout = QVBoxLayout()
        card_layout.setSpacing(SPACING_MD)

        # Results table (with provider & confidence columns)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Filename", "Size (MB)", "Target Path", "Provider", "Confidence", "Status"
        ])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setMinimumHeight(260)
        card_layout.addWidget(self.results_table, stretch=1)
        self._show_empty_state()

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        card_layout.addWidget(self.progress)

        # Bottom row: export buttons on the left, primary actions on the right
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(SPACING_LG)

        export_csv_btn = QPushButton("Export CSV")
        export_csv_btn.setObjectName("secondaryButton")
        export_csv_btn.clicked.connect(self._export_operations_csv)
        export_csv_btn.setMaximumWidth(150)
        bottom_layout.addWidget(export_csv_btn)

        export_json_btn = QPushButton("Export JSON")
        export_json_btn.setObjectName("secondaryButton")
        export_json_btn.clicked.connect(self._export_operations_json)
        export_json_btn.setMaximumWidth(150)
        bottom_layout.addWidget(export_json_btn)

        bottom_layout.addStretch()

        undo_btn = QPushButton("Undo Last")
        undo_btn.setObjectName("secondaryButton")
        undo_btn.clicked.connect(self._undo_last)
        undo_btn.setMinimumWidth(120)
        bottom_layout.addWidget(undo_btn)

        self.organize_btn = QPushButton("Rename && Copy")
        self.organize_btn.clicked.connect(self._execute_plan)
        self.organize_btn.setMinimumWidth(150)
        bottom_layout.addWidget(self.organize_btn)

        card_layout.addLayout(bottom_layout)

        card.setLayout(card_layout)
        return card

    def _toggle_theme(self):
        """Switch between dark and light themes and persist the choice."""
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings.set_theme(self.theme)
        self.setStyleSheet(get_stylesheet(self.theme))
        self.theme_btn.setText("☀ Light Mode" if self.theme == "dark" else "🌙 Dark Mode")
        self.status_theme.setText(f"🌙 {self.theme.capitalize()}")
    
    def _setup_status_bar(self):
        """Setup status bar with readability improvements and cache stats."""
        status = self.statusBar()
        status.setContentsMargins(SPACING_SM, 2, SPACING_SM, 2)

        self.status_ready = QLabel("✔ Ready")
        self.status_files = QLabel("📁 0 Files")
        self.status_mode = QLabel("🎯 Copy")
        self.status_operation = QLabel("📂 Rename & Copy")
        self.status_cache = QLabel("💾 Cache: 0H / 0M")
        self.status_theme = QLabel(f"🌙 {self.theme.capitalize()}")
        
        status.addWidget(self.status_ready)
        status.addWidget(QLabel("|"))
        status.addWidget(self.status_files)
        status.addWidget(QLabel("|"))
        status.addWidget(self.status_mode)
        status.addWidget(QLabel("|"))
        status.addWidget(self.status_operation)
        status.addWidget(QLabel("|"))
        status.addWidget(self.status_cache)
        status.addWidget(QLabel("|"))
        status.addWidget(self.status_theme)
    
    def _select_source(self):
        """Select source directory."""
        path = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if path:
            self.source_path = Path(path)
            self.source_path_label.setText(str(self.source_path))
    
    def _select_output(self):
        """Select output directory."""
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.output_path = Path(path)
            self.output_path_label.setText(str(self.output_path))
    
    def _scan_videos(self):
        """Scan source directory for videos using background matching."""
        if not self.source_path or not self.output_path:
            msg = ErrorHandler.from_exception(
                ValueError("Please select both source and output folders")
            )
            QMessageBox.warning(self, msg.title, msg.message)
            return
        
        # Save paths to settings
        self.settings.set_last_source_path(self.source_path)
        self.settings.set_last_destination_root(self.output_path)
        
        media_type_str = self.media_combo.currentText()
        media_type = MediaType(media_type_str)
        
        try:
            videos = self.scanner.scan_directory(self.source_path, media_type)
            
            if not videos:
                QMessageBox.information(self, "Info", "No video files found.")
                return
            self._start_match_batch(videos, media_type)
        except Exception as e:
            self._close_progress_dialog()
            error = ErrorHandler.from_exception(e)
            QMessageBox.critical(self, error.title, error.full_message())

    def _start_match_batch(self, videos, media_type):
        """Start a background match batch."""
        self._match_videos = videos
        self._match_media_type = media_type
        self._match_selected_provider = self.provider_combo.currentText()
        self.cache_stats = {"hits": 0, "misses": 0, "failures": 0}

        if self.provider_selector is None:
            self.provider_selector = ProviderSelector()
        if self.async_matcher is None:
            self.async_matcher = AsyncMatcher(max_workers=3, timeout=10)

        logger.info("Scan start: %s files", len(videos))
        logger.info("Selected provider: %s", self._match_selected_provider)

        self._close_progress_dialog()
        self.progress_dialog = ProgressDialog(
            self,
            "Scanning & Matching",
            "Parsing filenames...",
            len(videos)
        )
        self.progress_dialog.canceled.connect(self._cancel_match)
        self.progress_dialog.show()

        self.scan_btn.setEnabled(False)
        self.organize_btn.setEnabled(False)

        self.match_thread = QThread(self)
        self.match_worker = MatchWorker(
            filenames=[v.filename for v in videos],
            selector=self.provider_selector,
            matcher=self.async_matcher,
            selected_provider=self._match_selected_provider,
        )
        self.match_worker.moveToThread(self.match_thread)
        self.match_thread.started.connect(self.match_worker.run)
        self.match_worker.progress.connect(self._on_match_progress)
        self.match_worker.finished.connect(self._on_match_finished)
        self.match_worker.failed.connect(self._on_match_failed)
        self.match_worker.finished.connect(self.match_thread.quit)
        self.match_worker.failed.connect(self.match_thread.quit)
        self.match_thread.finished.connect(self._cleanup_match_thread)
        self.match_thread.start()

    def _on_match_progress(self, current, total, filename):
        """Update match progress UI."""
        self.progress_dialog.update_progress(current, total, filename)
        pct = int(current / total * 100) if total else 0
        self.statusBar().showMessage(f"Matching {current} / {total} | {pct}%")

    def _cancel_match(self):
        """Cancel the active match batch."""
        logger.info("Match cancelled by user")
        if self.match_worker:
            self.match_worker.cancel()

    def _on_match_failed(self, title, message):
        """Handle match worker failure."""
        logger.error("Match failed: %s - %s", title, message)
        self._close_progress_dialog()
        self.scan_btn.setEnabled(True)
        self.organize_btn.setEnabled(True)
        QMessageBox.critical(self, title, message)

    def _on_match_finished(self, results, attempts, completed):
        """Finalize match results on the UI thread."""
        try:
            matches = self._merge_match_results(self._match_videos, results, attempts)
            if not matches:
                QMessageBox.information(self, "Info", "No matches found.")
                return

            self.current_matches = matches
            self.match_report = MatchReport.from_matches(
                matches=[(m, m.provider.value) for m in matches],
                provider_stats=self.cache_stats
            )

            logger.info("Scan end: %s matches", len(matches))
            logger.info(self.match_report.summary())

            operation_type = "rename_copy" if self.copy_mode_check.isChecked() else "rename_move"
            self.current_plan = self.engine.plan_operations(
                matches=matches,
                media_type=self._match_media_type,
                destination_root=self.output_path,
                operation_type=operation_type,
                is_dry_run=False,
            )
            self._display_plan()
            self.status_files.setText(f"📁 {len(matches)} Files")
            self.status_cache.setText(
                f"💾 Cache: {self.cache_stats['hits']}H / {self.cache_stats['misses']}M"
            )
            self.statusBar().showMessage(f"Ready | Matched: {len(matches)} files")
        except Exception as e:
            logger.error("Match finalization failed: %s", e, exc_info=True)
            error = ErrorHandler.from_exception(e)
            QMessageBox.critical(self, error.title, error.full_message())
        finally:
            self._close_progress_dialog()
            self.scan_btn.setEnabled(True)
            self.organize_btn.setEnabled(True)

    def _merge_match_results(self, videos, results, attempts=None):
        """Merge provider matches with parsed filename metadata.

        A None result can mean two different things and they must not be
        conflated: (1) the automatic chain genuinely fell through to the
        Offline provider, or Offline was selected directly - a real
        success, or (2) a specific external provider (TMDB/AniList/MAL/
        TVMaze) was attempted and failed. Both used to be rendered
        identically as "Offline" with no trace of the failure. Case (2)
        now increments cache_stats['failures'] (surfaced by MatchReport
        as "API Failures") and records the failure reason on the match,
        instead of silently disappearing into a false "Offline" success.
        """
        matches = []
        matcher = AdvancedMatcher()
        attempts = attempts or [{}] * len(videos)
        failures = 0

        for video, result, attempt in zip(videos, results, attempts):
            parsed = None
            if video and video.filename:
                parsed = matcher.parse_filename(video.filename)

            attempted_provider = (attempt or {}).get("provider")
            attempt_status = (attempt or {}).get("status")
            attempt_error = (attempt or {}).get("error")
            is_offline_attempt = bool(attempted_provider) and attempted_provider.lower() == "offline"
            real_provider_failed = result is None and attempted_provider and not is_offline_attempt

            if result is None:
                error_message = None
                if real_provider_failed:
                    failures += 1
                    error_message = f"{attempted_provider} failed ({attempt_status}): {attempt_error}"
                    logger.warning(
                        "Provider failed: provider=%s query=%s status=%s error=%s -> using local parse fallback",
                        attempted_provider, video.filename, attempt_status, attempt_error,
                    )
                match = MatchResult(
                    source_path=video.path,
                    filename=video.filename,
                    provider=MatchProvider.OFFLINE,
                    confidence=parsed.get("confidence", 0.5) if parsed else 0.5,
                    title=parsed.get("title", video.filename.split('.')[0]) if parsed else video.filename.split('.')[0],
                    series_name=parsed.get("title", video.filename.split('.')[0]) if parsed else video.filename.split('.')[0],
                    season=parsed.get("season") if parsed else None,
                    episode=parsed.get("episode") if parsed else None,
                    year=parsed.get("year") if parsed else None,
                    destination_root=self.output_path,
                    status="Needs Review",
                    error_message=error_message,
                )
            else:
                match = result
                match.source_path = video.path
                match.filename = video.filename
                match.destination_root = self.output_path
                if not match.series_name:
                    match.series_name = match.title
                if parsed:
                    if match.season is None:
                        match.season = parsed.get("season")
                    if match.episode is None:
                        match.episode = parsed.get("episode")
                    if match.year is None:
                        match.year = parsed.get("year")
                match.proposed_filename = self.engine._build_proposed_filename(match)
                match.status = "Needs Review" if match.confidence < 0.8 else "Matched"
                logger.info(
                    "Match finalized: provider=%s query=%s confidence=%.2f series=%s season=%s episode=%s",
                    match.provider.value, video.filename, match.confidence,
                    match.series_name, match.season, match.episode,
                )
            matches.append(match)

        self.cache_stats["failures"] = self.cache_stats.get("failures", 0) + failures
        return matches

    def _close_progress_dialog(self):
        """Close any active progress dialog safely."""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

    def _cleanup_match_thread(self):
        """Release match worker resources."""
        self.match_worker = None
        self.match_thread = None
    
    def _display_plan(self):
        """Display organization plan in table with provider and confidence."""
        self.results_table.setRowCount(0)
        
        if not self.current_plan:
            self._show_empty_state()
            return
        
        for op in self.current_plan.operations:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            self.results_table.setRowHeight(row, 48)
            
            # Find corresponding match for provider/confidence info
            match = next((m for m in self.current_matches if m.source_path == op.source_path), None)
            
            # Filename with better typography
            filename_item = QTableWidgetItem(op.source_path.name)
            filename_font = QFont()
            filename_font.setPointSize(LIST_ITEM_FONT)
            filename_font.setBold(True)
            filename_item.setFont(filename_font)
            filename_item.setForeground(QColor(PRIMARY_TEXT))
            self.results_table.setItem(row, 0, filename_item)
            
            # Size
            try:
                size_mb = op.source_path.stat().st_size / 1024 / 1024
                size_item = QTableWidgetItem(f"{size_mb:.1f} MB")
            except Exception:
                size_item = QTableWidgetItem("N/A")
            size_item.setTextAlignment(Qt.AlignRight)
            self.results_table.setItem(row, 1, size_item)
            
            # Target path
            path_item = QTableWidgetItem(str(op.destination_path))
            path_font = QFont()
            path_font.setPointSize(LIST_PATH_FONT)
            path_item.setFont(path_font)
            path_item.setForeground(QColor(SECONDARY_TEXT))
            self.results_table.setItem(row, 2, path_item)
            
            # Provider (from match) - reflects the provider that actually
            # produced this match's metadata, e.g. TMDB stays TMDB on
            # success; only genuine Offline fallbacks/selections show Offline.
            provider_text = match.provider.value if match else "Unknown"
            provider_item = QTableWidgetItem(provider_text)
            provider_item.setForeground(QColor(SECONDARY_TEXT))
            if match and match.error_message:
                provider_item.setToolTip(match.error_message)
            self.results_table.setItem(row, 3, provider_item)
            
            # Confidence (from match)
            confidence_text = f"{int(match.confidence * 100)}%" if match else "N/A"
            confidence_item = QTableWidgetItem(confidence_text)
            confidence_item.setTextAlignment(Qt.AlignCenter)
            confidence_item.setForeground(QColor(SECONDARY_TEXT))
            self.results_table.setItem(row, 4, confidence_item)
            
            # Status - reflects match.status (e.g. "Needs Review" when a
            # selected provider failed and fell back to local parsing)
            # rather than always claiming "Ready".
            status_text = match.status if match else "Ready"
            status_item = QTableWidgetItem(status_text)
            status_color = ACCENT_SUCCESS if status_text == "Matched" else ACCENT_WARNING
            status_item.setForeground(QColor(status_color))
            if match and match.error_message:
                status_item.setToolTip(match.error_message)
            self.results_table.setItem(row, 5, status_item)
        
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.progress.setValue(0)
        
        # Update status bar
        file_count = len(self.current_plan.operations)
        self.status_files.setText(f"📁 {file_count} Files")
        self.status_operation.setText("📂 Rename & Copy" if self.copy_mode_check.isChecked() else "📂 Rename & Move")
    
    def _show_empty_state(self):
        """Show empty state message."""
        self.results_table.setRowCount(1)
        self.results_table.setRowHeight(0, 100)
        
        empty_item = QTableWidgetItem("⬇ Scan videos to see results")
        empty_item.setForeground(QColor(MUTED_TEXT))
        empty_font = QFont()
        empty_font.setPointSize(14)
        empty_item.setFont(empty_font)
        empty_item.setTextAlignment(Qt.AlignCenter)
        
        self.results_table.setItem(0, 0, empty_item)
        self.results_table.setSpan(0, 0, 1, 6)  # Updated to 6 columns
    
    def _execute_plan(self):
        """Execute the organization plan."""
        if not self.current_plan:
            msg = ErrorHandler.from_exception(
                ValueError("No plan to execute. Please scan files first.")
            )
            QMessageBox.warning(self, msg.title, msg.message)
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Operation",
            f"Organize {len(self.current_plan.operations)} files?"
        )
        if reply != QMessageBox.Yes:
            logger.info("Operation cancelled by user")
            return
        
        logger.info("Operation start: %s files", len(self.current_plan.operations))
        self.scan_btn.setEnabled(False)
        self.organize_btn.setEnabled(False)
        self.progress.setValue(0)
        self.operation_dialog = ProgressDialog(
            self,
            "Rename & Copy",
            "Preparing operation...",
            max(1, len(self.current_plan.operations))
        )
        self.operation_dialog.canceled.connect(self._cancel_operation)
        self.operation_dialog.show()

        self.operation_thread = QThread(self)
        self.operation_worker = OperationWorker(
            self.engine,
            self.current_plan,
            verify_after_copy=self.settings.get_verify_after_copy(),
        )
        self.operation_worker.moveToThread(self.operation_thread)
        self.operation_thread.started.connect(self.operation_worker.run)
        self.operation_worker.progress.connect(self._on_operation_progress)
        self.operation_worker.finished.connect(self._on_operation_finished)
        self.operation_worker.failed.connect(self._on_operation_failed)
        self.operation_worker.finished.connect(self.operation_thread.quit)
        self.operation_worker.failed.connect(self.operation_thread.quit)
        self.operation_thread.finished.connect(self._cleanup_operation_thread)
        self.operation_thread.start()

    def _on_operation_progress(self, payload):
        """Update operation progress."""
        current = payload.get("current", 0)
        total = payload.get("total", 1)
        current_file = payload.get("current_file", "")
        if self.operation_dialog:
            self.operation_dialog.update_progress(current, total, current_file)
        self.progress.setValue(int(current / total * 100) if total else 0)
        self.statusBar().showMessage(f"Operation {current}/{total} | {current_file}")

    def _cancel_operation(self):
        """Cancel the active file operation."""
        logger.info("Operation cancelled by user")
        if self.operation_worker:
            self.operation_worker.cancel()

    def _on_operation_finished(self, result):
        """Handle completed file operation."""
        logger.info(
            "Operation end: %s successful, %s failed, %s skipped",
            len(result.successful),
            len(result.failed),
            len(result.skipped),
        )
        message = f"✓ {len(result.successful)} files organized"
        if result.failed:
            message += f"\n✗ {len(result.failed)} failed"
        if result.skipped:
            message += f"\n⊘ {len(result.skipped)} skipped"
        self._close_operation_dialog()
        self.scan_btn.setEnabled(True)
        self.organize_btn.setEnabled(True)
        self.progress.setValue(100 if result.successful else 0)
        QMessageBox.information(self, "Operation Complete", message)

    def _on_operation_failed(self, title, message):
        """Handle operation failure."""
        logger.error("Operation failed: %s - %s", title, message)
        self._close_operation_dialog()
        self.scan_btn.setEnabled(True)
        self.organize_btn.setEnabled(True)
        error = ErrorHandler.from_exception(Exception(message))
        QMessageBox.critical(self, title, error.message)

    def _close_operation_dialog(self):
        """Close operation dialog safely."""
        if self.operation_dialog:
            self.operation_dialog.close()
            self.operation_dialog = None

    def _cleanup_operation_thread(self):
        """Release operation worker resources."""
        self.operation_worker = None
        self.operation_thread = None
    
    def _undo_last(self):
        """Undo the last batch operation."""
        undo_ops = self.logger.pop_undo_batch()
        if not undo_ops:
            QMessageBox.information(self, "Undo", "Nothing to undo.")
            return
        
        # Show confirmation dialog if setting enabled
        if self.settings.get_confirm_before_undo():
            confirm_dialog = ConfirmUndoDialog(self, len(undo_ops))
            if confirm_dialog.exec() != QDialog.Accepted or not confirm_dialog.was_confirmed():
                # User cancelled, restore the ops to undo stack
                self.logger.push_undo_batch(undo_ops)
                return
        
        # Undo operations in reverse order
        success_count = 0
        fail_count = 0
        for op in reversed(undo_ops):
            try:
                if self.logger.undo_operation(op):
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error("Undo failed for operation %s: %s", op, e)
                fail_count += 1
        
        message = f"✓ Undone {success_count} operations"
        if fail_count:
            message += f"\n✗ {fail_count} could not be undone"
        
        QMessageBox.information(self, "Undo Complete", message)
        self._scan_videos()  # Refresh display
    
    def _on_provider_changed(self, provider_name: str):
        """Handle provider selection change."""
        self.settings.set_provider(provider_name.lower())
        
        # Update API key button visibility
        if provider_name.lower() in {"offline", "automatic"}:
            self.provider_key_btn.setEnabled(False)
            self.provider_key_btn.setToolTip("Selected provider doesn't need an API key")
        else:
            self.provider_key_btn.setEnabled(True)
            self.provider_key_btn.setToolTip(f"Configure {provider_name} API key")
    
    def _configure_api_key(self):
        """Show API key configuration dialog."""
        provider_name = self.provider_combo.currentText()
        provider_key = {
            "TMDB": "tmdb",
            "AniList": "anilist",
            "MyAnimeList": "mal",
            "TVMaze": "tvmaze",
        }.get(provider_name)
        
        if provider_key is None:
            QMessageBox.information(
                self,
                "No API Key Required",
                f"{provider_name} doesn't need an API key."
            )
            return
        
        current_key = self.settings.get_api_key(provider_key) or ""
        
        dialog = APIKeyDialog(self, provider_name, current_key)
        if dialog.exec() == QDialog.Accepted:
            key = dialog.get_api_key()
            if key:
                self.settings.set_api_key(provider_key, key)
                QMessageBox.information(
                    self,
                    "Success",
                    f"{provider_name} API key saved successfully."
                )
            else:
                QMessageBox.warning(self, "Error", "API key cannot be empty.")
    
    def _export_operations_csv(self):
        """Export operation log to CSV."""
        path = QFileDialog.getSaveFileName(
            self,
            "Save Operations as CSV",
            str(Path.home() / "operations.csv"),
            "CSV Files (*.csv)"
        )[0]
        
        if path:
            if self.logger.export_csv(Path(path)):
                self.statusBar().showMessage(f"Operations exported to CSV: {path}")
                QMessageBox.information(self, "Export Successful", f"Operations exported to:\n{path}")
            else:
                QMessageBox.warning(self, "Export Failed", "Could not export operations to CSV.")
    
    def _export_operations_json(self):
        """Export operation log to JSON."""
        path = QFileDialog.getSaveFileName(
            self,
            "Save Operations as JSON",
            str(Path.home() / "operations.json"),
            "JSON Files (*.json)"
        )[0]
        
        if path:
            if self.logger.export_json(Path(path)):
                self.statusBar().showMessage(f"Operations exported to JSON: {path}")
                QMessageBox.information(self, "Export Successful", f"Operations exported to:\n{path}")
            else:
                QMessageBox.warning(self, "Export Failed", "Could not export operations to JSON.")


class ModernMediaForgeWindow(MediaForgeApp):
    """Approved modern MediaForge window."""
    pass
