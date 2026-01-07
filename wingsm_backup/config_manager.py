"""Configuration management for WinGSM Backup Manager."""
import json
import os
from pathlib import Path
from typing import Optional

from .models import ApplicationConfig


class ConfigManager:
    """Manages application configuration persistence."""

    def __init__(self):
        """Initialize the configuration manager."""
        app_data_path = Path(os.getenv("LOCALAPPDATA", "")) / "WinGSMBackup"
        app_data_path.mkdir(parents=True, exist_ok=True)
        self.config_path = app_data_path / "config.json"
        self._config: Optional[ApplicationConfig] = None
        self.load()

    def load(self) -> ApplicationConfig:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._config = ApplicationConfig.from_dict(data)
            except Exception:
                self._config = self._create_default_config()
        else:
            self._config = self._create_default_config()

        return self._config

    def save(self):
        """Save configuration to file."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_config(self) -> ApplicationConfig:
        """Get the current configuration."""
        if self._config is None:
            self.load()
        return self._config

    def update_config(self, config: ApplicationConfig):
        """Update and save configuration."""
        self._config = config
        self.save()

    def _create_default_config(self) -> ApplicationConfig:
        """Create default configuration."""
        default_backup_path = Path.home() / "Documents" / "WinGSMBackups"
        default_backup_path.mkdir(parents=True, exist_ok=True)

        return ApplicationConfig(
            windowsgsm_path="",
            default_backup_path=str(default_backup_path)
        )

