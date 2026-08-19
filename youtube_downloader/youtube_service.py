"""Couche métier autour de yt-dlp.

L'interface ne connaît plus les dizaines d'options yt-dlp : elle transmet une
requête typée et reçoit des callbacks. Cette séparation rend les changements
YouTube beaucoup plus faciles à corriger à l'avenir.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yt_dlp
from yt_dlp.version import __version__ as YT_DLP_VERSION

from .logs import LogBuffer, YtDlpLogger
from .models import DownloadKind, DownloadRequest, SearchResult, VideoQuality


ProgressHook = Callable[[dict[str, Any]], None]
StatusCallback = Callable[[str], None]


class DownloadOptionsFactory:
    """Fabrique les options yt-dlp à partir d'une requête utilisateur."""

    _H264_FORMATS: dict[VideoQuality, str] = {
        VideoQuality.H264_BEST: (
            "bestvideo[vcodec^=avc1]+bestaudio/"
            "bestvideo+bestaudio/best"
        ),
        VideoQuality.P1080: (
            "bestvideo[height<=1080][vcodec^=avc1]+bestaudio/"
            "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        ),
        VideoQuality.P720: (
            "bestvideo[height<=720][vcodec^=avc1]+bestaudio/"
            "bestvideo[height<=720]+bestaudio/best[height<=720]"
        ),
        VideoQuality.P480: (
            "bestvideo[height<=480][vcodec^=avc1]+bestaudio/"
            "bestvideo[height<=480]+bestaudio/best[height<=480]"
        ),
    }

    _H264_CONVERT_ARGS = [
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "23",
        "-c:a",
        "aac",
    ]

    def __init__(self, ffmpeg_path: Path | None, logger: YtDlpLogger) -> None:
        self._ffmpeg_path = ffmpeg_path
        self._logger = logger

    def build(self, request: DownloadRequest, progress_hook: ProgressHook) -> dict[str, Any]:
        request.destination.mkdir(parents=True, exist_ok=True)

        options: dict[str, Any] = {
            "logger": self._logger,
            "verbose": True,
            "progress_hooks": [progress_hook],
            "outtmpl": str(request.destination / "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,
            "socket_timeout": 20,
            "noplaylist": not request.playlist,
            # yt-dlp utilise Deno pour résoudre les challenges JS récents.
            "remote_components": {"ejs:github"},
            "js_runtimes": {"deno": {}},
        }

        self._apply_cookies(options, request.cookies_browser)
        self._apply_ffmpeg(options)

        if request.kind is DownloadKind.AUDIO:
            self._configure_audio(options)
        else:
            self._configure_video(options, request.quality)

        return options

    def build_compatibility(
        self,
        request: DownloadRequest,
        progress_hook: ProgressHook,
    ) -> dict[str, Any]:
        """Options volontairement simples utilisées après un échec réseau/format.

        Le mode de secours ne fige aucun client YouTube. Les clients internes
        changent régulièrement côté YouTube ; les forcer ici transformerait un
        correctif ponctuel en nouvelle panne au changement suivant. On laisse
        donc la version courante de yt-dlp appliquer sa propre stratégie.
        """

        options: dict[str, Any] = {
            "logger": self._logger,
            "verbose": True,
            "progress_hooks": [progress_hook],
            "outtmpl": str(request.destination / "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,
            "socket_timeout": 30,
            "format": "best" if request.kind is DownloadKind.VIDEO else "bestaudio/best",
            "noplaylist": not request.playlist,
            "remote_components": {"ejs:github"},
            "js_runtimes": {"deno": {}},
        }

        self._apply_cookies(options, request.cookies_browser)
        self._apply_ffmpeg(options)

        if request.kind is DownloadKind.AUDIO and self._ffmpeg_path:
            self._configure_audio(options)
        elif request.kind is DownloadKind.VIDEO and self._ffmpeg_path:
            options["merge_output_format"] = "mp4"
            options["postprocessors"] = [
                {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
            ]

        return options

    @staticmethod
    def _apply_cookies(options: dict[str, Any], browser: str | None) -> None:
        if browser:
            options["cookiesfrombrowser"] = (browser.lower(),)

    def _apply_ffmpeg(self, options: dict[str, Any]) -> None:
        if not self._ffmpeg_path:
            return

        location = self._ffmpeg_path.parent if self._ffmpeg_path.is_file() else self._ffmpeg_path
        options["ffmpeg_location"] = str(location)

    @staticmethod
    def _configure_audio(options: dict[str, Any]) -> None:
        options.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
        )

    def _configure_video(self, options: dict[str, Any], quality: VideoQuality) -> None:
        # Sans FFmpeg, yt-dlp doit récupérer un flux déjà multiplexé.
        if not self._ffmpeg_path:
            options["format"] = "best"
            return

        options["merge_output_format"] = "mp4"

        if quality is VideoQuality.VP9_4K:
            options["format"] = "bestvideo+bestaudio/best"
            return

        options["format"] = self._H264_FORMATS[quality]
        options["postprocessors"] = [
            {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
        ]
        options["postprocessor_args"] = {
            "videoconvertor": self._H264_CONVERT_ARGS.copy()
        }


class YouTubeService:
    """Façade utilisée par l'UI pour télécharger, rechercher et prévisualiser."""

    def __init__(self, ffmpeg_path: Path | None, logs: LogBuffer) -> None:
        self._ffmpeg_path = ffmpeg_path
        self._logs = logs

    def set_ffmpeg_path(self, path: Path | None) -> None:
        self._ffmpeg_path = path

    def download(
        self,
        request: DownloadRequest,
        progress_hook: ProgressHook,
        status_callback: StatusCallback,
    ) -> bool:
        """Télécharge avec une stratégie normale puis un mode de compatibilité.

        Retourne `True` si le mode standard a fonctionné et `False` si le mode
        de secours a été nécessaire.
        """

        self._logs.clear()
        self._logs.append(f"[INFO] Moteur yt-dlp : {YT_DLP_VERSION}")
        logger = YtDlpLogger(status_callback, self._logs)
        factory = DownloadOptionsFactory(self._ffmpeg_path, logger)

        try:
            self._run_download(request.url, factory.build(request, progress_hook))
            return True
        except yt_dlp.utils.DownloadError as standard_error:
            self._logs.append(f"[WARNING] Échec du mode standard : {standard_error}")
            status_callback("Mode standard échoué, tentative de compatibilité...")

        self._logs.append("[INFO] Passage en mode compatibilité.")
        self._run_download(
            request.url,
            factory.build_compatibility(request, progress_hook),
        )
        return False

    @staticmethod
    def _run_download(url: str, options: dict[str, Any]) -> None:
        with yt_dlp.YoutubeDL(options) as ydl:
            error_code = ydl.download([url])
            if error_code:
                raise yt_dlp.utils.DownloadError(
                    f"yt-dlp a terminé avec le code d'erreur {error_code}."
                )

    def search(self, query: str, limit: int = 15) -> list[SearchResult]:
        options: dict[str, Any] = {
            "quiet": True,
            "extract_flat": True,
            "ignoreerrors": True,
            "socket_timeout": 15,
            "remote_components": {"ejs:github"},
            "js_runtimes": {"deno": {}},
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)

        entries = (info or {}).get("entries") or []
        return [SearchResult.from_yt_dlp(entry) for entry in entries if entry]

    def preview_stream(
        self,
        url: str,
        cookies_browser: str | None,
    ) -> tuple[str, str]:
        options: dict[str, Any] = {
            "format": "best[height<=480]/best",
            "quiet": True,
            "socket_timeout": 15,
            "remote_components": {"ejs:github"},
            "js_runtimes": {"deno": {}},
        }
        if cookies_browser:
            options["cookiesfrombrowser"] = (cookies_browser.lower(),)

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info or not info.get("url"):
            raise yt_dlp.utils.DownloadError("Aucun flux de prévisualisation disponible.")

        return str(info["url"]), str(info.get("title") or "Preview")
