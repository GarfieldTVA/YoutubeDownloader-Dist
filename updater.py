"""Petit processus chargé de remplacer l'application après sa fermeture."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


LOG_PATH = Path(tempfile.gettempdir()) / "youtube_downloader_updater.log"
MAX_WAIT_SECONDS = 15
REPLACE_ATTEMPTS = 8


def configure_logging() -> None:
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        encoding="utf-8",
    )


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def wait_for_process(pid: int) -> None:
    deadline = time.monotonic() + MAX_WAIT_SECONDS
    while process_exists(pid) and time.monotonic() < deadline:
        time.sleep(0.25)

    if process_exists(pid):
        logging.warning("Le processus %s ne s'est pas fermé à temps ; SIGTERM envoyé.", pid)
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        time.sleep(1)


def replace_application(source: Path, target: Path) -> None:
    """Remplace la cible en conservant un backup jusqu'au succès.

    Le backup permet de restaurer l'ancienne version si le déplacement de la
    nouvelle application échoue au mauvais moment.
    """

    backup = target.with_name(target.name + ".bak")
    if backup.exists():
        shutil.rmtree(backup) if backup.is_dir() else backup.unlink()

    last_error: Exception | None = None
    for attempt in range(1, REPLACE_ATTEMPTS + 1):
        try:
            if target.exists():
                shutil.move(str(target), str(backup))

            shutil.move(str(source), str(target))

            if os.name != "nt" and target.is_file():
                target.chmod(target.stat().st_mode | 0o111)

            if backup.exists():
                shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
            logging.info("Remplacement réussi à la tentative %s.", attempt)
            return
        except Exception as error:  # Le détail est journalisé pour le diagnostic.
            last_error = error
            logging.exception("Échec du remplacement (%s/%s).", attempt, REPLACE_ATTEMPTS)

            # Si la nouvelle cible n'existe pas mais que le backup oui, on restaure.
            if not target.exists() and backup.exists():
                try:
                    shutil.move(str(backup), str(target))
                except Exception:
                    logging.exception("Impossible de restaurer le backup.")

            time.sleep(0.75)

    raise RuntimeError("Impossible de remplacer l'application.") from last_error


def relaunch(target: Path) -> None:
    kwargs: dict[str, object] = {}
    if os.name != "nt":
        kwargs["start_new_session"] = True
    subprocess.Popen([str(target)], **kwargs)


def main() -> int:
    configure_logging()

    if len(sys.argv) != 4:
        logging.error("Arguments invalides : %r", sys.argv)
        return 2

    try:
        pid = int(sys.argv[1])
        source = Path(sys.argv[2]).resolve()
        target = Path(sys.argv[3]).resolve()

        logging.info("Update demandé : pid=%s source=%s target=%s", pid, source, target)
        wait_for_process(pid)
        time.sleep(0.75)  # Laisse Windows libérer les derniers handles de fichier.
        replace_application(source, target)
        relaunch(target)
        return 0
    except Exception:
        logging.exception("Échec critique de la mise à jour.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
