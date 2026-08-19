"""Objets de données échangés entre l'interface et les services métier."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class DownloadKind(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"


class VideoQuality(str, Enum):
    H264_BEST = "Best (H.264)"
    P1080 = "1080p"
    P720 = "720p"
    P480 = "480p"
    VP9_4K = "4K (VP9)"


@dataclass(frozen=True, slots=True)
class DownloadRequest:
    """Description immuable d'un téléchargement demandé par l'utilisateur."""

    url: str
    destination: Path
    kind: DownloadKind
    quality: VideoQuality
    playlist: bool = False
    cookies_browser: str | None = None


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Vue simplifiée d'un résultat YouTube, indépendante du format yt-dlp."""

    title: str
    url: str
    channel: str
    duration_seconds: int | None
    thumbnail_url: str | None

    @classmethod
    def from_yt_dlp(cls, entry: dict[str, Any]) -> "SearchResult":
        thumbnail = entry.get("thumbnail")

        # yt-dlp peut fournir plusieurs formes de miniature selon le client.
        if isinstance(thumbnail, list) and thumbnail:
            last = thumbnail[-1]
            thumbnail = last.get("url") if isinstance(last, dict) else last
        elif isinstance(thumbnail, dict):
            thumbnail = thumbnail.get("url")

        if not thumbnail and entry.get("id"):
            thumbnail = f"https://i.ytimg.com/vi/{entry['id']}/mqdefault.jpg"

        raw_duration = entry.get("duration")
        try:
            duration = int(raw_duration) if raw_duration is not None else None
        except (TypeError, ValueError):
            duration = None

        raw_url = str(entry.get("webpage_url") or entry.get("url") or "")
        if raw_url and not raw_url.startswith(("http://", "https://")):
            video_id = str(entry.get("id") or raw_url)
            raw_url = f"https://www.youtube.com/watch?v={video_id}"

        return cls(
            title=str(entry.get("title") or "Titre inconnu"),
            url=raw_url,
            channel=str(entry.get("uploader") or "Chaîne inconnue"),
            duration_seconds=duration,
            thumbnail_url=str(thumbnail) if thumbnail else None,
        )
