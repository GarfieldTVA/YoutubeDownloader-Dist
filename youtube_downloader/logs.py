"""Gestion des logs et adaptateur attendu par yt-dlp."""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock


StatusCallback = Callable[[str], None]


class LogBuffer:
    """Petit buffer thread-safe destiné à la fenêtre de logs de l'application."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._lock = Lock()

    def append(self, line: str) -> None:
        with self._lock:
            self._lines.append(line)

    def clear(self) -> None:
        with self._lock:
            self._lines.clear()

    def snapshot(self) -> list[str]:
        with self._lock:
            return self._lines.copy()


class YtDlpLogger:
    """Adaptateur minimal vers l'API logger de yt-dlp.

    Les messages de progression `[download]` sont déjà traités via les hooks ;
    les réafficher dans le statut rendrait l'interface inutilement bruyante.
    """

    def __init__(self, status_callback: StatusCallback, log_buffer: LogBuffer) -> None:
        self._status_callback = status_callback
        self._log_buffer = log_buffer

    def debug(self, message: str) -> None:
        self._log_buffer.append(f"[DEBUG] {message}")
        if not message.startswith(("[download]", "[debug] ")):
            self._status_callback(message)

    def info(self, message: str) -> None:
        self._log_buffer.append(f"[INFO] {message}")
        if not message.startswith("[download]"):
            self._status_callback(message)

    def warning(self, message: str) -> None:
        self._log_buffer.append(f"[WARNING] {message}")

    def error(self, message: str) -> None:
        self._log_buffer.append(f"[ERROR] {message}")
        self._status_callback(f"Erreur : {message}")
