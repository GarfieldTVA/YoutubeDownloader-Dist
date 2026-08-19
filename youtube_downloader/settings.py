"""Persistance des préférences utilisateur."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import DEFAULT_THEME


class SettingsStore:
    """Stocke les réglages dans un JSON avec écriture atomique.

    Écrire d'abord dans un fichier temporaire évite de laisser un JSON tronqué
    si l'application est interrompue pendant la sauvegarde.
    """

    DEFAULTS: dict[str, Any] = {"appearance_mode": DEFAULT_THEME}

    def __init__(self, path: Path) -> None:
        self._path = path
        self._data = self.DEFAULTS.copy()

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return self._data.copy()

        try:
            with self._path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
            if isinstance(loaded, dict):
                self._data.update(loaded)
        except (OSError, json.JSONDecodeError):
            # Un fichier utilisateur corrompu ne doit jamais empêcher le démarrage.
            pass

        return self._data.copy()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(self._path.suffix + ".tmp")

        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(self._data, file, ensure_ascii=False, indent=2)

        temp_path.replace(self._path)
