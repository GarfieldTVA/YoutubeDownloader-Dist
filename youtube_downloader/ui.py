"""Interface CustomTkinter de YouTube Downloader Ultimate."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys
import threading
import tkinter.messagebox
from typing import Any, TypeVar

import customtkinter as ctk

from .config import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_COLOR_THEME,
    DEFAULT_THEME,
    DEFAULT_WINDOW_SIZE,
    AppPaths,
)
from .dependencies import DependencyManager
from .logs import LogBuffer
from .settings import SettingsStore
from .update_service import UpdateInfo, UpdateService
from .youtube_service import YouTubeService
from .ui_download import DownloadTabMixin
from .ui_search import SearchTabMixin


T = TypeVar("T")


class YouTubeDownloaderApp(DownloadTabMixin, SearchTabMixin, ctk.CTk):
    """Fenêtre principale.

    Cette classe orchestre l'interface uniquement. Les opérations longues sont
    déléguées à des services puis exécutées dans des threads daemon afin de ne
    jamais bloquer la boucle Tkinter.
    """

    def __init__(self) -> None:
        self.paths = AppPaths.detect()
        self.paths.data_dir.mkdir(parents=True, exist_ok=True)

        self.logs = LogBuffer()
        self.settings_store = SettingsStore(self.paths.settings_file)
        settings = self.settings_store.load()

        ctk.set_appearance_mode(str(settings.get("appearance_mode", DEFAULT_THEME)))
        ctk.set_default_color_theme(DEFAULT_COLOR_THEME)

        super().__init__()
        self.title(f"{APP_NAME} - v{APP_VERSION}")
        self.geometry(DEFAULT_WINDOW_SIZE)
        self.minsize(780, 620)

        self.download_folder = self.paths.downloads_dir
        self.dependencies = DependencyManager(self.paths, self.logs)
        self.dependencies.ensure_directories()
        self.dependencies.add_bin_to_path()

        self.ffmpeg_path = self.dependencies.find_ffmpeg()
        self.youtube = YouTubeService(self.ffmpeg_path, self.logs)
        self.updates = UpdateService(self.paths, self.logs)

        self._configure_layout()
        self._build_tabs()
        self._bootstrap_dependencies()
        self._check_updates_when_frozen()

    # ------------------------------------------------------------------
    # Initialisation générale
    # ------------------------------------------------------------------

    def _configure_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _build_tabs(self) -> None:
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.tab_download = self.tabview.add("Téléchargement Direct")
        self.tab_search = self.tabview.add("Recherche YouTube")

        self._setup_download_tab()
        self._setup_search_tab()

    def _bootstrap_dependencies(self) -> None:
        if self.ffmpeg_path is None and sys.platform == "win32":
            self._run_background(
                self.dependencies.install_ffmpeg_windows,
                on_success=self._on_ffmpeg_installed,
                on_error=lambda error: self.logs.append(
                    f"[ERROR] Installation FFmpeg impossible : {error}"
                ),
            )

        if self.dependencies.find_deno() is None:
            self._run_background(
                self.dependencies.install_deno,
                on_error=lambda error: self.logs.append(
                    f"[ERROR] Installation Deno impossible : {error}"
                ),
            )

    def _on_ffmpeg_installed(self, path: Path) -> None:
        self.ffmpeg_path = path
        self.youtube.set_ffmpeg_path(path)
        self._set_status("FFmpeg installé. Prêt.", color="green")

    def _check_updates_when_frozen(self) -> None:
        if not getattr(sys, "frozen", False):
            return

        self._run_background(
            self.updates.check,
            on_success=self._offer_update,
            on_error=lambda error: self.logs.append(
                f"[UPDATE] Vérification impossible : {error}"
            ),
        )

    def _offer_update(self, update: UpdateInfo | None) -> None:
        if update is None:
            return

        accepted = tkinter.messagebox.askyesno(
            "Mise à jour disponible",
            f"La version {update.version} est disponible.\n\n"
            "Voulez-vous la télécharger et redémarrer l'application ?",
        )
        if not accepted:
            return

        self._set_status("Téléchargement de la mise à jour...")
        self._run_background(
            lambda: self.updates.prepare_and_launch(update),
            on_success=lambda _result: self.destroy(),
            on_error=lambda error: tkinter.messagebox.showerror(
                "Erreur de mise à jour",
                str(error),
            ),
        )

    # ------------------------------------------------------------------
    # Outils de concurrence / UI
    # ------------------------------------------------------------------

    def _run_background(
        self,
        action: Callable[[], T],
        *,
        on_success: Callable[[T], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Exécute une fonction hors du thread Tkinter.

        Tous les callbacks sont rematriçés vers la boucle principale avec
        `after()`. C'est un détail important : Tkinter n'est pas thread-safe.
        """

        def worker() -> None:
            try:
                result = action()
            except Exception as error:
                self.logs.append(f"[ERROR] {type(error).__name__}: {error}")
                if on_error:
                    self.after(0, lambda err=error: on_error(err))
                return

            if on_success:
                self.after(0, lambda: on_success(result))

        threading.Thread(target=worker, daemon=True).start()

    def _set_status(self, message: str, color: str | None = None) -> None:
        kwargs: dict[str, Any] = {"text": message}
        if color:
            kwargs["text_color"] = color
        self.label_status.configure(**kwargs)

    def _set_status_threadsafe(self, message: str) -> None:
        clean = str(message).strip()
        if len(clean) > 90:
            clean = clean[:87] + "..."
        self.after(0, lambda: self._set_status(clean))
