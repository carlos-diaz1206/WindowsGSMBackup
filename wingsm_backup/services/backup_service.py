"""Service for creating local backups."""
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import ServerBackupResult, ServerConfig


class BackupService:
    """Service for creating and managing backups."""

    def __init__(self, windowsgsm_service):
        """Initialize the backup service."""
        self.windowsgsm_service = windowsgsm_service

    async def backup_server(
        self, server: ServerConfig, backup_root_path: str
    ) -> ServerBackupResult:
        """Create a backup of a server's savegame files."""
        result = ServerBackupResult(
            server_id=server.server_id,
            server_name=server.server_name
        )

        try:
            savegame_path = Path(server.save_game_path)

            if not savegame_path.exists():
                result.success = False
                result.error_message = "Savegame path not found or invalid"
                return result

            # Create backup directory structure
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_dir = Path(backup_root_path) / server.server_id / timestamp
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Create zip archive
            zip_path = backup_dir / f"{server.server_name}_{timestamp}.zip"

            with zipfile.ZipFile(
                zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6
            ) as zipf:
                for file_path in savegame_path.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(savegame_path)
                        zipf.write(file_path, arcname)

            result.backup_path = str(zip_path)
            result.backup_size_bytes = zip_path.stat().st_size
            result.success = True

        except Exception as ex:
            result.success = False
            result.error_message = str(ex)

        return result

    def cleanup_old_backups(self, backup_root_path: str, retention_days: int):
        """Remove backups older than retention_days."""
        try:
            backup_root = Path(backup_root_path)
            if not backup_root.exists():
                return

            cutoff_date = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)

            for server_dir in backup_root.iterdir():
                if not server_dir.is_dir():
                    continue

                for backup_dir in server_dir.iterdir():
                    if not backup_dir.is_dir():
                        continue

                    try:
                        if backup_dir.stat().st_mtime < cutoff_date:
                            shutil.rmtree(backup_dir)
                    except Exception:
                        # Log error but continue
                        pass

        except Exception:
            # Log error
            pass

    def get_backup_size(self, backup_path: str) -> int:
        """Get the size of a backup file in bytes."""
        try:
            path = Path(backup_path)
            if path.exists():
                return path.stat().st_size
            return 0
        except Exception:
            return 0

