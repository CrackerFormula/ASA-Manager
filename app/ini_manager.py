import configparser
import os
from typing import Any

from app.config import settings


class IniManager:
    def __init__(self, path: str | None = None):
        self.path = path or settings.INI_PATH

    def _load(self) -> configparser.RawConfigParser:
        parser = configparser.RawConfigParser()
        parser.optionxform = str  # preserve case
        if os.path.exists(self.path):
            parser.read(self.path, encoding="utf-8")
        return parser

    def _save(self, parser: configparser.RawConfigParser) -> None:
        d = os.path.dirname(str(self.path))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            parser.write(f, space_around_delimiters=False)

    def read_all(self) -> dict[str, dict[str, str]]:
        parser = self._load()
        result: dict[str, dict[str, str]] = {}
        for section in parser.sections():
            result[section] = dict(parser.items(section))
        return result

    def read_section(self, section: str) -> dict[str, str]:
        parser = self._load()
        if not parser.has_section(section):
            return {}
        return dict(parser.items(section))

    def write_setting(self, section: str, key: str, value: Any) -> None:
        parser = self._load()
        if not parser.has_section(section):
            parser.add_section(section)
        parser.set(section, key, str(value))
        self._save(parser)

    def write_section(self, section: str, data: dict[str, Any]) -> None:
        parser = self._load()
        if not parser.has_section(section):
            parser.add_section(section)
        for key, value in data.items():
            parser.set(section, key, str(value))
        self._save(parser)


ini_manager = IniManager()
