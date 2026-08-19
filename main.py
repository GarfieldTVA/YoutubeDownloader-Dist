"""Point d'entrée de YouTube Downloader Ultimate."""

from youtube_downloader.ui import YouTubeDownloaderApp


def main() -> None:
    app = YouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
