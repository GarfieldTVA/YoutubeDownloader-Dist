"""Composant de l'onglet de téléchargement.

Le mixin ne contient que la présentation et l'orchestration de cet onglet ;
la logique yt-dlp reste dans :mod:`youtube_service`.
"""

from __future__ import annotations

from pathlib import Path
import tkinter.filedialog
import tkinter.messagebox
from typing import Any

import customtkinter as ctk

from .config import DEFAULT_THEME
from .models import DownloadKind, DownloadRequest, VideoQuality


class DownloadTabMixin:
    """Méthodes UI dédiées au téléchargement direct."""

    def _setup_download_tab(self) -> None:
        self.tab_download.grid_columnconfigure(0, weight=1)
        self.tab_download.grid_rowconfigure(5, weight=1)

        main = ctk.CTkFrame(self.tab_download, fg_color="transparent")
        main.grid(row=0, column=0, padx=40, pady=20, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            main,
            text="Lien de la vidéo / playlist",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray20", "#aaaaaa"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))

        url_frame = ctk.CTkFrame(
            main,
            fg_color=("#EBEBEB", "#2b2b2b"),
            corner_radius=10,
            border_width=1,
            border_color=("#D0D0D0", "#3a3a3a"),
        )
        url_frame.grid(row=1, column=0, sticky="ew", pady=(0, 25))
        url_frame.grid_columnconfigure(0, weight=1)

        self.entry_url = ctk.CTkEntry(
            url_frame,
            placeholder_text="https://www.youtube.com/watch?v=...",
            height=50,
            border_width=0,
            fg_color="transparent",
            font=ctk.CTkFont(size=15),
            text_color=("gray10", "white"),
        )
        self.entry_url.grid(row=0, column=0, padx=15, sticky="ew")

        ctk.CTkButton(
            url_frame,
            text="COLLER",
            width=80,
            height=36,
            fg_color=("#C0C0C0", "#444444"),
            hover_color=("#A0A0A0", "#555555"),
            text_color=("black", "white"),
            corner_radius=8,
            command=self._paste_url,
        ).grid(row=0, column=1, padx=10, pady=7)

        settings_frame = ctk.CTkFrame(main, fg_color="transparent")
        settings_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        settings_frame.grid_columnconfigure((0, 1), weight=1)

        self._build_format_panel(settings_frame)
        self._build_destination_panel(settings_frame)

        self.btn_download = ctk.CTkButton(
            main,
            text="LANCER LE TÉLÉCHARGEMENT",
            height=60,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#00A36C",
            hover_color="#008558",
            corner_radius=15,
            command=self._start_download,
        )
        self.btn_download.grid(row=3, column=0, sticky="ew", pady=(20, 10))

        self.progress_bar = ctk.CTkProgressBar(main, height=10, progress_color="#00A36C")
        self.progress_bar.grid(row=4, column=0, sticky="ew", padx=5)
        self.progress_bar.set(0)

        self.label_status = ctk.CTkLabel(
            main,
            text="Prêt",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        )
        self.label_status.grid(row=5, column=0, pady=5)

        self.cookies_var = ctk.StringVar(value="Sans Cookies")
        ctk.CTkOptionMenu(
            self.tab_download,
            variable=self.cookies_var,
            values=["Sans Cookies", "Chrome", "Firefox", "Edge", "Opera", "Brave"],
            width=110,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=("#DBDBDB", "#333333"),
            button_color=("#DBDBDB", "#333333"),
            text_color=("gray10", "gray"),
        ).place(relx=0.95, rely=0.98, anchor="se")

        ctk.CTkButton(
            self.tab_download,
            text="Logs",
            width=60,
            height=24,
            fg_color="transparent",
            border_width=1,
            border_color=("#aaaaaa", "#444444"),
            text_color=("gray20", "gray"),
            font=ctk.CTkFont(size=11),
            command=self._open_log_window,
        ).place(relx=0.05, rely=0.98, anchor="sw")

    def _build_format_panel(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent, fg_color=("#EBEBEB", "#232323"), corner_radius=10)
        frame.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text="Format & Qualité",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray20", "gray"),
        ).pack(padx=15, pady=(15, 10), anchor="w")

        self.type_var = ctk.StringVar(value=DownloadKind.VIDEO.value)
        self.seg_type = ctk.CTkSegmentedButton(
            frame,
            values=["Vidéo", "Audio"],
            command=self._on_download_kind_changed,
        )
        self.seg_type.pack(padx=15, pady=(0, 15), fill="x")
        self.seg_type.set("Vidéo")

        self.res_var = ctk.StringVar(value=VideoQuality.H264_BEST.value)
        self.option_res = ctk.CTkOptionMenu(
            frame,
            variable=self.res_var,
            values=[quality.value for quality in VideoQuality],
            fg_color=("#DBDBDB", "#333333"),
            button_color=("#DBDBDB", "#333333"),
            text_color=("gray10", "gray90"),
        )
        self.option_res.pack(padx=15, pady=(0, 20), fill="x")

    def _build_destination_panel(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent, fg_color=("#EBEBEB", "#232323"), corner_radius=10)
        frame.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text="Options & Destination",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray20", "gray"),
        ).pack(padx=15, pady=(15, 10), anchor="w")

        self.playlist_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            frame,
            text="Télécharger la playlist",
            variable=self.playlist_var,
        ).pack(padx=15, pady=(5, 10), anchor="w")

        ctk.CTkButton(
            frame,
            text="📂 Choisir le dossier",
            fg_color=("#DBDBDB", "#333333"),
            hover_color=("#C9C9C9", "#404040"),
            text_color=("gray10", "white"),
            anchor="w",
            command=self._choose_folder,
        ).pack(padx=15, pady=(5, 5), fill="x")

        self.label_folder = ctk.CTkLabel(
            frame,
            text=self._truncate_path(self.download_folder),
            text_color=("gray40", "gray"),
            font=ctk.CTkFont(size=11),
        )
        self.label_folder.pack(padx=15, pady=(0, 15), anchor="w")

        ctk.CTkLabel(
            frame,
            text="Thème :",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray20", "gray"),
        ).pack(padx=15, anchor="w")

        theme_menu = ctk.CTkOptionMenu(
            frame,
            values=["System", "Dark", "Light"],
            command=self._change_appearance,
            fg_color=("#DBDBDB", "#333333"),
            button_color=("#DBDBDB", "#333333"),
            text_color=("gray10", "gray90"),
        )
        theme_menu.pack(padx=15, pady=(0, 15), fill="x")
        theme_menu.set(str(self.settings_store.get("appearance_mode", DEFAULT_THEME)))

    def _on_download_kind_changed(self, label: str) -> None:
        if label == "Audio":
            self.type_var.set(DownloadKind.AUDIO.value)
            self.option_res.configure(state="disabled")
        else:
            self.type_var.set(DownloadKind.VIDEO.value)
            self.option_res.configure(state="normal")

    def _change_appearance(self, mode: str) -> None:
        ctk.set_appearance_mode(mode)
        self.settings_store.set("appearance_mode", mode)

    def _paste_url(self) -> None:
        try:
            text = self.clipboard_get()
        except tkinter.TclError:
            return
        self.entry_url.delete(0, "end")
        self.entry_url.insert(0, text)

    def _choose_folder(self) -> None:
        folder = tkinter.filedialog.askdirectory(initialdir=str(self.download_folder))
        if not folder:
            return
        self.download_folder = Path(folder)
        self.label_folder.configure(text=self._truncate_path(self.download_folder))

    @staticmethod
    def _truncate_path(path: Path, length: int = 50) -> str:
        value = str(path)
        if len(value) <= length:
            return value
        return "..." + value[-(length - 3) :]

    def _start_download(self) -> None:
        url = self.entry_url.get().strip()
        if not url:
            self._set_status("Erreur : veuillez entrer une URL.", color="red")
            return

        try:
            quality = VideoQuality(self.res_var.get())
        except ValueError:
            quality = VideoQuality.H264_BEST

        browser = self.cookies_var.get()
        request = DownloadRequest(
            url=url,
            destination=self.download_folder,
            kind=DownloadKind(self.type_var.get()),
            quality=quality,
            playlist=bool(self.playlist_var.get()),
            cookies_browser=None if browser == "Sans Cookies" else browser,
        )

        self.btn_download.configure(state="disabled")
        self.progress_bar.set(0)
        self._set_status("Analyse en cours...", color="white")

        self._run_background(
            lambda: self.youtube.download(
                request,
                progress_hook=self._progress_hook,
                status_callback=self._set_status_threadsafe,
            ),
            on_success=self._finish_download,
            on_error=lambda error: self._finish_download_error(str(error)),
        )

    def _progress_hook(self, data: dict[str, Any]) -> None:
        status = data.get("status")
        if status == "downloading":
            percent_text = str(data.get("_percent_str") or "0%").strip()
            try:
                value = max(0.0, min(1.0, float(percent_text.replace("%", "")) / 100.0))
            except ValueError:
                value = 0.0

            self.after(0, lambda: self.progress_bar.set(value))
            self.after(0, lambda: self._set_status(f"Téléchargement : {percent_text}"))
        elif status == "finished":
            self.after(0, lambda: self._set_status("Traitement / Conversion..."))

    def _finish_download(self, standard_mode: bool) -> None:
        message = (
            "Téléchargement terminé avec succès !"
            if standard_mode
            else "Téléchargement terminé (mode compatibilité) !"
        )
        self._set_status(message, color="green")
        self.progress_bar.set(1)
        self.btn_download.configure(state="normal")

    def _finish_download_error(self, message: str) -> None:
        self._set_status(f"Erreur : {message}", color="red")
        self.btn_download.configure(state="normal")

    def _open_log_window(self) -> None:
        window = ctk.CTkToplevel(self)
        window.title("Logs détaillés")
        window.geometry("800x600")

        textbox = ctk.CTkTextbox(window, width=780, height=540)
        textbox.pack(padx=10, pady=10, fill="both", expand=True)
        textbox.insert("1.0", "\n".join(self.logs.snapshot()))
        textbox.configure(state="disabled")

        ctk.CTkButton(
            window,
            text="Sauvegarder les logs",
            command=self._save_logs,
        ).pack(pady=(0, 10))

    def _save_logs(self) -> None:
        file_path = tkinter.filedialog.asksaveasfilename(
            initialdir=str(Path.home() / "Documents"),
            defaultextension=".txt",
            filetypes=[("Fichier texte", "*.txt")],
            title="Sauvegarder les logs",
        )
        if not file_path:
            return

        try:
            Path(file_path).write_text("\n".join(self.logs.snapshot()), encoding="utf-8")
        except OSError as error:
            tkinter.messagebox.showerror("Erreur", f"Impossible de sauvegarder les logs : {error}")
            return

        tkinter.messagebox.showinfo("Succès", f"Logs sauvegardés dans :\n{file_path}")
