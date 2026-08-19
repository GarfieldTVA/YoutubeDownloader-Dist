"""Configuration globale de l'application.

Ce module ne contient volontairement aucune logique métier : il centralise les
constantes afin d'éviter les valeurs magiques dispersées dans l'interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import sys


APP_NAME = "YouTube Downloader Ultimate"
APP_VERSION = "1.1.0"
APP_DATA_DIRNAME = "YouTubeDownloader"
UPDATE_CHECK_URL = (
    "https://raw.githubusercontent.com/"
    "GarfieldTVA/YoutubeDownloader-Dist/main/version.json"
)

DEFAULT_WINDOW_SIZE = "900x750"
DEFAULT_THEME = "Dark"
DEFAULT_COLOR_THEME = "blue"
DEFAULT_SEARCH_LIMIT = 15

FFMPEG_WINDOWS_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)
DENO_RELEASE_BASE_URL = "https://github.com/denoland/deno/releases/latest/download/"

# Une identité explicite évite de dépendre du User-Agent très ancien autrefois
# codé en dur dans l'application.
HTTP_USER_AGENT = f"{APP_NAME}/{APP_VERSION}"


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Chemins utilisés par l'application, calculés une seule fois au démarrage."""

    data_dir: Path
    bin_dir: Path
    settings_file: Path
    downloads_dir: Path

    @classmethod
    def detect(cls) -> "AppPaths":
        """Construit des chemins adaptés au système d'exploitation courant."""

        home = Path.home()

        if sys.platform == "win32":
            appdata = os.getenv("APPDATA")
            data_dir = Path(appdata) / APP_DATA_DIRNAME if appdata else home / APP_DATA_DIRNAME
        elif sys.platform == "darwin":
            data_dir = home / "Library" / "Application Support" / APP_DATA_DIRNAME
        else:
            data_dir = home / ".config" / APP_DATA_DIRNAME

        downloads = home / "Downloads"
        if not downloads.exists():
            downloads = home

        return cls(
            data_dir=data_dir,
            bin_dir=data_dir / "bin",
            settings_file=data_dir / "settings.json",
            downloads_dir=downloads,
        )
