#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install --upgrade --pre -r requirements.txt
rm -rf build dist ./*.spec

python -m PyInstaller --noconfirm --clean --onefile --console --name updater updater.py

extra=()
[[ -f ffmpeg ]] && extra+=(--add-binary "ffmpeg:.")
[[ -f ffplay ]] && extra+=(--add-binary "ffplay:.")

python -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name "YouTubeDownloader_v1.1.0" \
  --add-binary "dist/updater:." \
  "${extra[@]}" \
  main.py
