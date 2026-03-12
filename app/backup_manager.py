import logging
import os
import re
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SAVE_DIR = Path("/serverdata/ark-server/ShooterGame/Saved/")
BACKUP_DIR = Path("/serverdata/backups/")
MAX_BACKUPS = 10


class BackupManager:
    def __init__(
        self,
        save_dir: Path = SAVE_DIR,
        backup_dir: Path = BACKUP_DIR,
        max_backups: int = MAX_BACKUPS,
    ):
        self._save_dir = save_dir
        self._backup_dir = backup_dir
        self._max_backups = max_backups

    def _ensure_dir(self) -> None:
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        """Validate filename to prevent path traversal."""
        name = os.path.basename(filename)
        if not name or name != filename or ".." in name or "/" in name or "\\" in name:
            raise ValueError(f"Invalid filename: {filename!r}")
        if not re.fullmatch(r"[\w.\-]+", name):
            raise ValueError(f"Invalid filename characters: {filename!r}")
        return name

    def create_backup(self) -> dict:
        self._ensure_dir()
        if not self._save_dir.exists():
            raise FileNotFoundError(f"Save directory not found: {self._save_dir}")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}.tar.gz"
        filepath = self._backup_dir / filename

        with tarfile.open(filepath, "w:gz") as tar:
            tar.add(str(self._save_dir), arcname="Saved")

        size = filepath.stat().st_size
        logger.info("Created backup: %s (%d bytes)", filename, size)

        self._prune_old_backups()

        return {"filename": filename, "size": size, "timestamp": timestamp}

    def list_backups(self) -> list[dict]:
        self._ensure_dir()
        backups = []
        for f in sorted(self._backup_dir.glob("backup_*.tar.gz"), reverse=True):
            stat = f.stat()
            backups.append({
                "filename": f.name,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
        return backups

    def delete_backup(self, filename: str) -> None:
        filename = self._safe_filename(filename)
        filepath = self._backup_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Backup not found: {filename}")
        filepath.unlink()
        logger.info("Deleted backup: %s", filename)

    def restore_backup(self, filename: str) -> None:
        filename = self._safe_filename(filename)
        filepath = self._backup_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Backup not found: {filename}")

        # Remove existing save directory contents and extract
        if self._save_dir.exists():
            shutil.rmtree(self._save_dir)
        self._save_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(filepath, "r:gz") as tar:
            tar.extractall(path=self._save_dir.parent, filter="data")

        logger.info("Restored backup: %s", filename)

    def _prune_old_backups(self) -> None:
        backups = sorted(self._backup_dir.glob("backup_*.tar.gz"), reverse=True)
        for old in backups[self._max_backups:]:
            old.unlink()
            logger.info("Pruned old backup: %s", old.name)


backup_manager = BackupManager()
