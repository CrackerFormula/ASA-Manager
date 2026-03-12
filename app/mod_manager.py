import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

MODS_FILE = Path("/serverdata/config/mods.txt")


class ModManager:
    def __init__(self, path: Path = MODS_FILE):
        self._path = path

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate(mod_id: str) -> str:
        mod_id = mod_id.strip()
        if not re.fullmatch(r"\d+", mod_id):
            raise ValueError(f"Invalid mod ID: {mod_id!r} (must be numeric)")
        return mod_id

    def get_mods(self) -> list[str]:
        if not self._path.exists():
            return []
        lines = self._path.read_text().strip().splitlines()
        return [line.strip() for line in lines if line.strip()]

    def set_mods(self, mod_ids: list[str]) -> None:
        validated = [self._validate(m) for m in mod_ids]
        self._ensure_dir()
        self._path.write_text("\n".join(validated) + "\n" if validated else "")
        logger.info("Mods set to: %s", validated)

    def add_mod(self, mod_id: str) -> list[str]:
        mod_id = self._validate(mod_id)
        mods = self.get_mods()
        if mod_id not in mods:
            mods.append(mod_id)
            self.set_mods(mods)
            logger.info("Added mod %s", mod_id)
        return mods

    def remove_mod(self, mod_id: str) -> list[str]:
        mod_id = self._validate(mod_id)
        mods = self.get_mods()
        if mod_id in mods:
            mods.remove(mod_id)
            self.set_mods(mods)
            logger.info("Removed mod %s", mod_id)
        return mods


mod_manager = ModManager()
