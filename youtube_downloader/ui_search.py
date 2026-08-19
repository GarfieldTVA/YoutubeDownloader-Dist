"""Composant de recherche YouTube et de prévisualisation."""

from __future__ import annotations

import io
import subprocess
import sys
import tkinter.messagebox
from typing import Any
import urllib.request

import customtkinter as ctk
from PIL import Image

from .config import DEFAULT_SEARCH_LIMIT, HTTP_USER_AGENT
from .models import SearchResult


class SearchTabMixin:
    """Méthodes UI dédiées à la recherche et à la preview FFplay."""

    def _setup_search_tab(self) -> None:
        self.tab_search.grid_columnconfigure(0, weight=1)
        self.tab_search.grid_rowconfigure(1, weight=1)

        search_frame = ctk.CTkFrame(self.tab_search, fg_color="transparent")
        search_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        self.entry_search = ctk.CTkEntry(
            search_frame,
            placeholder_text="Rechercher sur YouTube...",
            height=40,
        )
        self.entry_search.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.entry_search.bind("<Return>", lambda _event: self._start_search())

        self.btn_search = ctk.CTkButton(
            search_frame,
            text="Rechercher",
            width=100,
            height=40,
            command=self._start_search,
        )
        self.btn_search.grid(row=0, column=1)

        self.scroll_results = ctk.CTkScrollableFrame(
            self.tab_search,
            label_text="Résultats",
            fg_color="transparent",
        )
        self.scroll_results.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.scroll_results.grid_columnconfigure(0, weight=1)

    def _start_search(self) -> None:
        query = self.entry_search.get().strip()
        if not query:
            return

        for widget in self.scroll_results.winfo_children():
            widget.destroy()

        loading = ctk.CTkLabel(self.scroll_results, text="Recherche en cours...")
        loading.pack(pady=20)
        self.btn_search.configure(state="disabled")

        self._run_background(
            lambda: self.youtube.search(query, DEFAULT_SEARCH_LIMIT),
            on_success=lambda results: self._display_results(results, loading),
            on_error=lambda error: self._display_search_error(error, loading),
        )

    def _display_search_error(self, error: Exception, loading: ctk.CTkLabel) -> None:
        self.btn_search.configure(state="normal")
        if loading.winfo_exists():
            loading.configure(text=f"Erreur : {error}")

    def _display_results(self, results: list[SearchResult], loading: ctk.CTkLabel) -> None:
        self.btn_search.configure(state="normal")
        if loading.winfo_exists():
            loading.destroy()

        if not results:
            ctk.CTkLabel(self.scroll_results, text="Aucun résultat trouvé.").pack(pady=20)
            return

        for result in results:
            self._create_result_card(result)

    def _create_result_card(self, result: SearchResult) -> None:
        frame = ctk.CTkFrame(
            self.scroll_results,
            fg_color=("#E8E8E8", "#232323"),
            corner_radius=12,
            border_width=1,
            border_color=("#D0D0D0", "#333333"),
        )
        frame.pack(fill="x", padx=10, pady=8)
        frame.grid_columnconfigure(1, weight=1)

        thumbnail = ctk.CTkLabel(
            frame,
            text="",
            width=192,
            height=108,
            fg_color=("#D0D0D0", "#111111"),
            corner_radius=8,
        )
        thumbnail.grid(row=0, column=0, rowspan=2, padx=12, pady=12)

        if result.thumbnail_url:
            self._run_background(
                lambda: self._download_thumbnail(result.thumbnail_url),
                on_success=lambda photo: self._apply_thumbnail(thumbnail, photo),
                on_error=lambda _error: thumbnail.configure(text="No Image"),
            )
        else:
            thumbnail.configure(text="No Image")

        info = ctk.CTkFrame(frame, fg_color="transparent")
        info.grid(row=0, column=1, rowspan=2, padx=5, pady=10, sticky="nsew")

        ctk.CTkLabel(
            info,
            text=result.title,
            anchor="w",
            justify="left",
            wraplength=400,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(fill="x", pady=(5, 5))

        ctk.CTkLabel(
            info,
            text=f"👤 {result.channel}   •   ⏱️ {self._format_duration(result.duration_seconds)}",
            anchor="w",
            justify="left",
            text_color="#aaaaaa",
            font=ctk.CTkFont(size=13),
        ).pack(fill="x")

        actions = ctk.CTkFrame(frame, fg_color="transparent")
        actions.grid(row=0, column=2, rowspan=2, padx=15, pady=10)

        ctk.CTkButton(
            actions,
            text="Télécharger",
            width=110,
            height=35,
            fg_color="#00A36C",
            hover_color="#008558",
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self._select_video(result.url),
        ).pack(pady=5)

        ctk.CTkButton(
            actions,
            text="Voir / Écouter",
            width=110,
            height=30,
            fg_color="#444444",
            hover_color="#555555",
            command=lambda: self._open_preview(result.url),
        ).pack(pady=5)

    @staticmethod
    def _download_thumbnail(url: str) -> Image.Image:
        """Télécharge et prépare une miniature sans créer d'objet Tkinter.

        Cette fonction tourne dans un worker. La création de `CTkImage` reste
        volontairement dans le thread principal, car Tkinter n'est pas thread-safe.
        """

        request = urllib.request.Request(url, headers={"User-Agent": HTTP_USER_AGENT})
        with urllib.request.urlopen(request, timeout=15) as response:
            raw_data = response.read()

        with Image.open(io.BytesIO(raw_data)) as image:
            resized = image.convert("RGB").resize((192, 108), Image.Resampling.LANCZOS)
            return resized.copy()

    @staticmethod
    def _apply_thumbnail(label: ctk.CTkLabel, image: Image.Image) -> None:
        """Crée l'image CustomTkinter sur le thread UI puis l'affiche."""

        if label.winfo_exists():
            photo = ctk.CTkImage(light_image=image, dark_image=image, size=(192, 108))
            label.configure(image=photo, text="")
            # Une référence explicite évite que Tkinter perde l'image après GC.
            label._youtube_thumbnail = photo  # type: ignore[attr-defined]

    @staticmethod
    def _format_duration(seconds: int | None) -> str:
        if seconds is None:
            return "??"
        minutes, second = divmod(seconds, 60)
        hours, minute = divmod(minutes, 60)
        return (
            f"{hours}:{minute:02d}:{second:02d}"
            if hours
            else f"{minute:02d}:{second:02d}"
        )

    def _select_video(self, url: str) -> None:
        self.entry_url.delete(0, "end")
        self.entry_url.insert(0, url)
        self.tabview.set("Téléchargement Direct")

    # ------------------------------------------------------------------
    # Preview FFplay
    # ------------------------------------------------------------------

    def _open_preview(self, url: str) -> None:
        browser = self.cookies_var.get()
        cookies = None if browser == "Sans Cookies" else browser

        self._run_background(
            lambda: self.youtube.preview_stream(url, cookies),
            on_success=self._launch_ffplay,
            on_error=lambda error: tkinter.messagebox.showerror(
                "Erreur",
                f"Impossible de lancer la preview : {error}",
            ),
        )

    def _launch_ffplay(self, stream: tuple[str, str]) -> None:
        stream_url, title = stream
        ffplay = self.dependencies.find_ffplay()
        if ffplay is None:
            tkinter.messagebox.showerror(
                "Erreur",
                "FFplay n'est pas disponible. Réinstallez FFmpeg ou relancez l'application.",
            )
            return

        command = [
            str(ffplay),
            "-window_title",
            f"Preview - {title}",
            "-autoexit",
            "-x",
            "800",
            "-y",
            "450",
            stream_url,
        ]

        kwargs: dict[str, Any] = {}
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs["startupinfo"] = startupinfo
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            subprocess.Popen(command, **kwargs)
        except OSError as error:
            tkinter.messagebox.showerror("Erreur", f"FFplay n'a pas pu démarrer : {error}")
