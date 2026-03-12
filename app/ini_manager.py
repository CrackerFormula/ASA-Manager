import asyncio
import logging
import os
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class IniManager:
    """Line-oriented INI parser that preserves duplicate keys, comments, and formatting."""

    def __init__(self, path: str | None = None):
        self.path = path or settings.INI_PATH
        self._lock = asyncio.Lock()

    # ── Internal data model ──────────────────────────────────────────
    # The file is stored as a list of "lines".  Each line is one of:
    #   ("section", section_name)           – a [SectionHeader]
    #   ("kv", key, value)                  – a Key=Value pair
    #   ("other", raw_text)                 – comment / blank / unparseable

    def _load(self) -> list[tuple]:
        """Parse the INI file into an ordered list of line-tuples."""
        lines: list[tuple] = []
        if not os.path.exists(self.path):
            logger.debug("INI file does not exist yet: %s", self.path)
            return lines
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for raw in f:
                    raw = raw.rstrip("\n").rstrip("\r")
                    stripped = raw.strip()
                    if stripped.startswith("[") and stripped.endswith("]"):
                        lines.append(("section", stripped[1:-1]))
                    elif "=" in stripped and not stripped.startswith(";") and not stripped.startswith("#"):
                        idx = raw.index("=")
                        key = raw[:idx].strip()
                        value = raw[idx + 1:]
                        lines.append(("kv", key, value))
                    else:
                        lines.append(("other", raw))
        except Exception:
            logger.exception("Failed to read INI file: %s", self.path)
        return lines

    def _save(self, lines: list[tuple]) -> None:
        """Write the line-tuples back to disk."""
        try:
            d = os.path.dirname(str(self.path))
            if d:
                os.makedirs(d, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                for entry in lines:
                    if entry[0] == "section":
                        f.write(f"[{entry[1]}]\n")
                    elif entry[0] == "kv":
                        f.write(f"{entry[1]}={entry[2]}\n")
                    else:
                        f.write(entry[1] + "\n")
        except Exception:
            logger.exception("Failed to write INI file: %s", self.path)
            raise

    # ── Helpers ───────────────────────────────────────────────────────

    def _section_range(self, lines: list[tuple], section: str) -> tuple[int | None, int]:
        """Return (start_index, end_index) for a section.  start_index is the
        index of the [section] header line; end_index is one-past the last
        kv/other line belonging to that section (i.e. up to the next section
        header or EOF).  Returns (None, len(lines)) if section not found."""
        start = None
        for i, entry in enumerate(lines):
            if entry[0] == "section" and entry[1] == section:
                start = i
                break
        if start is None:
            return None, len(lines)
        end = start + 1
        while end < len(lines) and lines[end][0] != "section":
            end += 1
        return start, end

    # ── Public API ────────────────────────────────────────────────────

    def read_all(self) -> dict[str, list[dict[str, str]]]:
        """Return all sections as {section_name: [{key, value}, ...]}."""
        lines = self._load()
        result: dict[str, list[dict[str, str]]] = {}
        current_section: str | None = None
        for entry in lines:
            if entry[0] == "section":
                current_section = entry[1]
                if current_section not in result:
                    result[current_section] = []
            elif entry[0] == "kv" and current_section is not None:
                result[current_section].append({"key": entry[1], "value": entry[2]})
        return result

    def read_section(self, section: str) -> list[dict[str, str]]:
        """Return list of {key, value} pairs for a single section."""
        lines = self._load()
        pairs: list[dict[str, str]] = []
        in_section = False
        for entry in lines:
            if entry[0] == "section":
                if entry[1] == section:
                    in_section = True
                elif in_section:
                    break
            elif entry[0] == "kv" and in_section:
                pairs.append({"key": entry[1], "value": entry[2]})
        return pairs

    def write_setting(self, section: str, key: str, value: Any) -> None:
        """Update the FIRST occurrence of *key* in *section*, or append."""
        lines = self._load()
        start, end = self._section_range(lines, section)

        if start is None:
            # Section doesn't exist yet — append it
            lines.append(("section", section))
            lines.append(("kv", key, str(value)))
            self._save(lines)
            return

        # Look for existing key
        for i in range(start + 1, end):
            if lines[i][0] == "kv" and lines[i][1] == key:
                lines[i] = ("kv", key, str(value))
                self._save(lines)
                return

        # Key not found — insert before end of section
        lines.insert(end, ("kv", key, str(value)))
        self._save(lines)

    def write_section(self, section: str, data: list[dict[str, Any]]) -> None:
        """Replace the entire content of *section* with *data* (list of {key, value})."""
        lines = self._load()
        start, end = self._section_range(lines, section)

        new_entries = [("kv", pair["key"], str(pair["value"])) for pair in data]

        if start is None:
            # Section doesn't exist — append
            lines.append(("section", section))
            lines.extend(new_entries)
        else:
            # Replace everything between header and next section
            lines[start + 1 : end] = new_entries

        self._save(lines)

    # ── Async wrappers (with lock) ────────────────────────────────────

    async def async_write_setting(self, section: str, key: str, value: Any) -> None:
        async with self._lock:
            self.write_setting(section, key, value)

    async def async_write_section(self, section: str, data: list[dict[str, Any]]) -> None:
        async with self._lock:
            self.write_section(section, data)


ini_manager = IniManager()
