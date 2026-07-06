#!/usr/bin/env python3
"""
MediaForge Organizer - Main entry point
"""
import sys
import logging
from PySide6.QtWidgets import QApplication
from mediaforge.app import ModernMediaForgeWindow


logger = logging.getLogger(__name__)


def main():
    """Launch the MediaForge Organizer application."""
    logger.info("Launching MediaForge from src.main")
    qt_app = QApplication(sys.argv)
    window = ModernMediaForgeWindow()
    window.show()
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
