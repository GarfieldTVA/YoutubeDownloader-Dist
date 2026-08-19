"""Détection et installation des dépendances externes FFmpeg / Deno."""

from __future__ import annotations

import os
import platform
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import urllib.request
import zipfile

from .config import DENO_RELEASE_BASE_URL, FFMPEG_WINDOWS_URL, HTTP_USER_AGENT, AppPaths
from .logs import LogBuffer


class DependencyManager:
    """Centralise les dépendances système utilisées par yt-dlp et la preview."""

    def __init__(self, paths: AppPaths, logs: LogBuffer) -> None:
        self.paths = paths
        self.logs = logs

    def ensure_directories(self) -> None:
        self.paths.data_dir.mkdir(parents=True, exist_ok=True)
        self.paths.bin_dir.mkdir(parents=True, exist_ok=True)

    def add_bin_to_path(self) -> None:
        bin_path = str(self.paths.bin_dir)
        current = os.environ.get("PATH", "")
        entries = current.split(os.pathsep) if current else []
        if bin_path not in entries:
            os.environ["PATH"] = current + (os.pathsep if current else "") + bin_path
            self.logs.append(f"[INFO] Ajout de {bin_path} au PATH")

    def find_ffmpeg(self) -> Path | None:
        executable = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        candidates: list[Path] = []

        if getattr(sys, "frozen", False):
            meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
            candidates.extend((meipass / executable, Path(sys.executable).parent / executable))

        candidates.extend((Path.cwd() / executable, self.paths.data_dir / executable))

        for candidate in candidates:
            if candidate.is_file():
                return candidate

        discovered = shutil.which("ffmpeg")
        return Path(discovered) if discovered else None

    def find_ffplay(self) -> Path | None:
        executable = "ffplay.exe" if sys.platform == "win32" else "ffplay"
        candidates: list[Path] = []

        if getattr(sys, "frozen", False):
            meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
            candidates.extend((meipass / executable, Path(sys.executable).parent / executable))

        candidates.extend((Path.cwd() / executable, self.paths.data_dir / executable))

        for candidate in candidates:
            if candidate.is_file():
                return candidate

        discovered = shutil.which("ffplay")
        return Path(discovered) if discovered else None

    def find_deno(self) -> Path | None:
        executable = "deno.exe" if sys.platform == "win32" else "deno"
        local = self.paths.bin_dir / executable
        if local.is_file():
            return local

        discovered = shutil.which("deno")
        return Path(discovered) if discovered else None

    def install_ffmpeg_windows(self) -> Path:
        """Installe FFmpeg et FFplay dans AppData sur Windows.

        L'archive est téléchargée dans un fichier temporaire, puis seuls les
        exécutables attendus sont extraits. On évite ainsi un `extractall()` sur
        une archive distante.
        """

        if sys.platform != "win32":
            raise RuntimeError("L'installation automatique de FFmpeg est réservée à Windows.")

        ffmpeg_target = self.paths.data_dir / "ffmpeg.exe"
        ffplay_target = self.paths.data_dir / "ffplay.exe"
        if ffmpeg_target.exists() and ffplay_target.exists():
            return ffmpeg_target

        self.logs.append("[INFO] Téléchargement de FFmpeg...")
        archive_path = self._download_to_temp(FFMPEG_WINDOWS_URL, suffix=".zip")

        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                wanted = {
                    "bin/ffmpeg.exe": ffmpeg_target,
                    "bin/ffplay.exe": ffplay_target,
                }
                found: set[str] = set()

                for member in archive.namelist():
                    normalized = member.replace("\\", "/")
                    for suffix, target in wanted.items():
                        if normalized.endswith(suffix):
                            with archive.open(member) as source, target.open("wb") as destination:
                                shutil.copyfileobj(source, destination)
                            found.add(suffix)

                if "bin/ffmpeg.exe" not in found:
                    raise RuntimeError("ffmpeg.exe est absent de l'archive téléchargée.")
        finally:
            archive_path.unlink(missing_ok=True)

        self.logs.append("[INFO] FFmpeg installé avec succès.")
        return ffmpeg_target

    def install_deno(self) -> Path:
        """Télécharge la bonne archive Deno pour la plateforme courante."""

        self.paths.bin_dir.mkdir(parents=True, exist_ok=True)
        executable = "deno.exe" if sys.platform == "win32" else "deno"
        target = self.paths.bin_dir / executable
        if target.is_file():
            return target

        archive_name = self._deno_archive_name()
        url = DENO_RELEASE_BASE_URL + archive_name
        self.logs.append(f"[INFO] Téléchargement de Deno : {archive_name}")
        archive_path = self._download_to_temp(url, suffix=".zip")

        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                member = next(
                    (name for name in archive.namelist() if Path(name).name == executable),
                    None,
                )
                if member is None:
                    raise RuntimeError(f"{executable} est absent de l'archive Deno.")

                with archive.open(member) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
        finally:
            archive_path.unlink(missing_ok=True)

        if sys.platform != "win32":
            target.chmod(target.stat().st_mode | stat.S_IEXEC)

        self.add_bin_to_path()
        self.logs.append("[INFO] Deno installé avec succès.")
        return target

    @staticmethod
    def _deno_archive_name() -> str:
        machine = platform.machine().lower()

        if sys.platform == "win32":
            return "deno-x86_64-pc-windows-msvc.zip"
        if sys.platform == "darwin":
            return (
                "deno-aarch64-apple-darwin.zip"
                if machine in {"arm64", "aarch64"}
                else "deno-x86_64-apple-darwin.zip"
            )
        if machine in {"arm64", "aarch64"}:
            return "deno-aarch64-unknown-linux-gnu.zip"
        return "deno-x86_64-unknown-linux-gnu.zip"

    @staticmethod
    def _download_to_temp(url: str, suffix: str) -> Path:
        request = urllib.request.Request(url, headers={"User-Agent": HTTP_USER_AGENT})

        with urllib.request.urlopen(request, timeout=60) as response:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                shutil.copyfileobj(response, temp_file)
                return Path(temp_file.name)
