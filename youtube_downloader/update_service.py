"""Vérification et préparation des mises à jour de l'application."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile

from .config import APP_VERSION, HTTP_USER_AGENT, UPDATE_CHECK_URL, AppPaths
from .logs import LogBuffer


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    version: str
    download_url: str


class UpdateService:
    """Gère l'update sans mélanger réseau, UI et manipulation de fichiers."""

    def __init__(self, paths: AppPaths, logs: LogBuffer) -> None:
        self._paths = paths
        self._logs = logs

    def check(self) -> UpdateInfo | None:
        """Retourne une mise à jour uniquement si sa version est plus récente."""

        self._logs.append("[UPDATE] Vérification des mises à jour...")
        request = urllib.request.Request(
            UPDATE_CHECK_URL,
            headers={"User-Agent": HTTP_USER_AGENT},
        )

        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))

        remote_version = str(payload.get("version") or "0")
        download_url = self._select_platform_url(payload)

        if not download_url:
            self._logs.append("[UPDATE] Aucun binaire disponible pour cette plateforme.")
            return None

        if self._version_key(remote_version) <= self._version_key(APP_VERSION):
            self._logs.append("[UPDATE] Logiciel à jour.")
            return None

        self._logs.append(f"[UPDATE] Nouvelle version détectée : {remote_version}")
        return UpdateInfo(version=remote_version, download_url=download_url)

    def prepare_and_launch(self, update: UpdateInfo) -> None:
        """Télécharge l'asset, prépare le binaire et délègue le remplacement.

        Le remplacement du processus courant est volontairement confié à un
        petit updater séparé : sous Windows, un EXE en cours d'exécution est
        verrouillé et ne peut pas se remplacer lui-même proprement.
        """

        self._paths.data_dir.mkdir(parents=True, exist_ok=True)
        downloaded = self._download(update.download_url)
        replacement = self._extract_if_needed(downloaded)

        if not getattr(sys, "frozen", False):
            raise RuntimeError(
                f"Mise à jour téléchargée dans {replacement}. "
                "Le redémarrage automatique est désactivé en mode développement."
            )

        target = self._current_application_path()
        updater = self._copy_bundled_updater_to_temp()

        command = [str(updater), str(os.getpid()), str(replacement), str(target)]
        kwargs: dict[str, object] = {"close_fds": True}
        if sys.platform != "win32":
            kwargs["start_new_session"] = True

        self._logs.append(f"[UPDATE] Lancement de l'updater : {updater.name}")
        subprocess.Popen(command, **kwargs)

    def _download(self, url: str) -> Path:
        suffix = self._suffix_from_url(url)
        target = self._paths.data_dir / f"update_{int(time.time())}{suffix}"
        temporary = target.with_suffix(target.suffix + ".part")

        request = urllib.request.Request(url, headers={"User-Agent": HTTP_USER_AGENT})
        self._logs.append(f"[UPDATE] Téléchargement : {url}")

        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as file:
            expected = int(response.headers.get("Content-Length") or 0)
            downloaded = 0

            while chunk := response.read(1024 * 256):
                file.write(chunk)
                downloaded += len(chunk)

            file.flush()
            os.fsync(file.fileno())

        if expected and downloaded != expected:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(
                f"Téléchargement incomplet : {downloaded}/{expected} octets."
            )

        temporary.replace(target)
        self._logs.append(f"[UPDATE] {downloaded} octets téléchargés.")
        return target

    def _extract_if_needed(self, downloaded: Path) -> Path:
        lower_name = downloaded.name.lower()
        if lower_name.endswith(".zip"):
            return self._extract_zip(downloaded)
        if lower_name.endswith((".tar.gz", ".tgz")):
            return self._extract_tar(downloaded)
        return downloaded

    def _extract_zip(self, archive_path: Path) -> Path:
        destination = self._fresh_extract_dir()
        with zipfile.ZipFile(archive_path, "r") as archive:
            for member in archive.infolist():
                self._assert_safe_member(destination, member.filename)
                archive.extract(member, destination)
        return self._find_application_asset(destination)

    def _extract_tar(self, archive_path: Path) -> Path:
        destination = self._fresh_extract_dir()
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            for member in members:
                self._assert_safe_member(destination, member.name)
                if member.issym() or member.islnk():
                    raise RuntimeError("L'archive de mise à jour contient un lien symbolique refusé.")
            archive.extractall(destination, members=members)
        return self._find_application_asset(destination)

    def _fresh_extract_dir(self) -> Path:
        destination = self._paths.data_dir / "update_extracted"
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True)
        return destination

    @staticmethod
    def _assert_safe_member(destination: Path, member_name: str) -> None:
        """Bloque les chemins `../` afin d'éviter un Zip/Tar Slip."""

        candidate = (destination / member_name).resolve()
        root = destination.resolve()
        if candidate != root and root not in candidate.parents:
            raise RuntimeError(f"Chemin dangereux dans l'archive : {member_name}")

    @staticmethod
    def _find_application_asset(root: Path) -> Path:
        if sys.platform == "darwin":
            apps = [path for path in root.rglob("*.app") if path.is_dir()]
            if apps:
                return max(apps, key=UpdateService._path_size)

        files = [path for path in root.rglob("*") if path.is_file()]
        preferred = [
            path
            for path in files
            if "youtubedownloader" in path.name.lower()
            and path.stat().st_size > 1024 * 1024
        ]
        candidates = preferred or [path for path in files if path.stat().st_size > 1024 * 1024]

        if not candidates:
            raise RuntimeError("Aucun exécutable valide trouvé dans l'archive de mise à jour.")

        result = max(candidates, key=lambda path: path.stat().st_size)
        if sys.platform != "win32":
            result.chmod(result.stat().st_mode | stat.S_IEXEC)
        return result

    @staticmethod
    def _path_size(path: Path) -> int:
        if path.is_file():
            return path.stat().st_size
        return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())

    @staticmethod
    def _current_application_path() -> Path:
        executable = Path(sys.executable).resolve()
        if sys.platform == "darwin":
            for parent in executable.parents:
                if parent.suffix == ".app":
                    return parent
        return executable

    @staticmethod
    def _copy_bundled_updater_to_temp() -> Path:
        updater_name = "updater.exe" if sys.platform == "win32" else "updater"
        bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        source = bundle_dir / updater_name
        if not source.is_file():
            raise RuntimeError(f"Updater introuvable dans le paquet : {updater_name}")

        destination = Path(tempfile.gettempdir()) / (
            f"youtube_downloader_updater_{os.getpid()}_{int(time.time())}"
            + (".exe" if sys.platform == "win32" else "")
        )
        shutil.copy2(source, destination)
        if sys.platform != "win32":
            destination.chmod(destination.stat().st_mode | stat.S_IEXEC)
        return destination

    @staticmethod
    def _select_platform_url(payload: dict[str, object]) -> str:
        assets = payload.get("assets")
        if isinstance(assets, dict):
            if sys.platform == "win32":
                return str(assets.get("windows") or payload.get("url") or "")
            if sys.platform == "darwin":
                return str(assets.get("macos") or assets.get("darwin") or "")
            return str(assets.get("linux") or "")

        legacy = str(payload.get("url") or "")
        if sys.platform != "win32" and legacy.lower().endswith(".exe"):
            return ""
        return legacy

    @staticmethod
    def _version_key(version: str) -> tuple[int, ...]:
        """Compare les versions numériquement au lieu de comparer des chaînes."""

        numbers = [int(part) for part in re.findall(r"\d+", version)]
        return tuple(numbers or [0])

    @staticmethod
    def _suffix_from_url(url: str) -> str:
        clean = url.split("?", 1)[0].lower()
        if clean.endswith(".tar.gz"):
            return ".tar.gz"
        if clean.endswith(".tgz"):
            return ".tgz"
        suffix = Path(clean).suffix
        return suffix if suffix else (".exe" if sys.platform == "win32" else ".bin")
