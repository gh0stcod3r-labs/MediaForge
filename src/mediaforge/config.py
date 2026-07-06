"""Settings and configuration management for MediaForge Organizer."""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import json

from .models import MediaType


@dataclass
class AppSettings:
    """Application settings persisted to disk."""
    
    # Theme
    theme: str = "dark"  # "dark" or "light"
    
    # Provider selection
    provider: str = "offline"  # "tmdb", "anilist", "mal", "tvmaze", "offline"
    
    # Operation mode
    operation_mode: str = "rename_copy"  # "rename_only", "rename_copy", "rename_move", "folders_only"
    
    # Paths
    last_source_path: Optional[str] = None
    last_destination_root: Optional[str] = None
    
    # Window geometry
    window_width: int = 1000
    window_height: int = 600
    window_x: int = 100
    window_y: int = 100
    
    # Media type preference
    default_media_type: str = MediaType.ANIME.value
    
    # API keys (stored locally, never in repo)
    api_keys: dict = None  # e.g. {"tmdb": "xxx", "anilist": "yyy"}
    
    # Behavior
    verify_after_copy: bool = True
    confirm_before_undo: bool = True
    
    def __post_init__(self):
        if self.api_keys is None:
            self.api_keys = {}


class SettingsManager:
    """Manage application settings persistence."""
    
    def __init__(self):
        """Initialize settings manager."""
        self.config_dir = Path.home() / ".mediaforge"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.config_dir / "settings.json"
        self.settings = self._load()
    
    def _load(self) -> AppSettings:
        """Load settings from disk or create defaults."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                return AppSettings(**data)
            except Exception:
                # If corrupted, start fresh
                return AppSettings()
        return AppSettings()
    
    def save(self) -> None:
        """Save settings to disk."""
        try:
            with open(self.settings_file, "w") as f:
                json.dump(asdict(self.settings), f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to save settings: {e}")
    
    def get_theme(self) -> str:
        """Get current theme."""
        return self.settings.theme
    
    def set_theme(self, theme: str) -> None:
        """Set theme and persist."""
        self.settings.theme = theme
        self.save()
    
    def get_provider(self) -> str:
        """Get selected provider."""
        return self.settings.provider
    
    def set_provider(self, provider: str) -> None:
        """Set selected provider and persist."""
        self.settings.provider = provider
        self.save()
    
    def get_operation_mode(self) -> str:
        """Get selected operation mode."""
        return self.settings.operation_mode
    
    def set_operation_mode(self, mode: str) -> None:
        """Set operation mode and persist."""
        self.settings.operation_mode = mode
        self.save()
    
    def get_last_source_path(self) -> Optional[Path]:
        """Get last used source path."""
        if self.settings.last_source_path:
            path = Path(self.settings.last_source_path)
            if path.exists():
                return path
        return None
    
    def set_last_source_path(self, path: Path) -> None:
        """Save last used source path."""
        self.settings.last_source_path = str(path)
        self.save()
    
    def get_last_destination_root(self) -> Optional[Path]:
        """Get last used destination root."""
        if self.settings.last_destination_root:
            path = Path(self.settings.last_destination_root)
            if path.exists():
                return path
        return None
    
    def set_last_destination_root(self, path: Path) -> None:
        """Save last used destination root."""
        self.settings.last_destination_root = str(path)
        self.save()
    
    def get_window_geometry(self) -> tuple[int, int, int, int]:
        """Get saved window geometry (x, y, width, height)."""
        return (
            self.settings.window_x,
            self.settings.window_y,
            self.settings.window_width,
            self.settings.window_height,
        )
    
    def set_window_geometry(self, x: int, y: int, width: int, height: int) -> None:
        """Save window geometry."""
        self.settings.window_x = x
        self.settings.window_y = y
        self.settings.window_width = width
        self.settings.window_height = height
        self.save()
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for provider (stored locally, never in code)."""
        return self.settings.api_keys.get(provider)
    
    def set_api_key(self, provider: str, key: str) -> None:
        """Set API key for provider."""
        self.settings.api_keys[provider] = key
        self.save()
    
    def delete_api_key(self, provider: str) -> None:
        """Delete API key for provider."""
        self.settings.api_keys.pop(provider, None)
        self.save()
    
    def get_verify_after_copy(self) -> bool:
        """Get verify-after-copy setting."""
        return self.settings.verify_after_copy
    
    def set_verify_after_copy(self, enabled: bool) -> None:
        """Set verify-after-copy setting."""
        self.settings.verify_after_copy = enabled
        self.save()
    
    def get_confirm_before_undo(self) -> bool:
        """Get confirm-before-undo setting."""
        return self.settings.confirm_before_undo
    
    def set_confirm_before_undo(self, enabled: bool) -> None:
        """Set confirm-before-undo setting."""
        self.settings.confirm_before_undo = enabled
        self.save()


# Global settings instance
_settings_manager = None


def get_settings() -> SettingsManager:
    """Get global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager
