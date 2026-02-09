#!/bin/bash

echo "==================================================="
echo "    COMPILATION DU DOWNLOADER YOUTUBE (UNIX)"
echo "==================================================="
echo ""

# Installation des dépendances
echo "Installation des dépendances..."
pip3 install -r requirements.txt

echo ""
echo "Nettoyage des anciens builds..."
rm -rf build dist
rm -f *.spec

echo ""
echo "Lancement de PyInstaller pour UPDATER..."
# On Linux/Mac, updater usually doesn't need an extension
python3 -m PyInstaller --noconfirm --onefile --console --name "updater" updater.py

echo ""
echo "Lancement de PyInstaller pour MAIN APP..."
echo "Cela peut prendre quelques minutes..."
echo ""

# Check for ffmpeg binary
FFMPEG_ARG=""
if [ -f "ffmpeg" ]; then
    echo "FFmpeg trouvé, inclusion dans le paquet..."
    FFMPEG_ARG="--add-data ffmpeg:."
else
    echo "AVERTISSEMENT: ffmpeg non trouvé à la racine. L'application devra le télécharger."
fi

# Note the separator is ':' for Unix in --add-data
python3 -m PyInstaller --noconfirm --onefile --windowed --name "YouTubeDownloader_v1.0.3" --icon="NONE" $FFMPEG_ARG --add-data "dist/updater:." main.py

# Compression pour la distribution
echo ""
echo "Compression de l'exécutable..."
cd dist
if [ "$(uname)" == "Darwin" ]; then
    # macOS: zip
    zip -r "YouTubeDownloader_v1.0.3.zip" "YouTubeDownloader_v1.0.3.app" "YouTubeDownloader_v1.0.3" 2>/dev/null || zip "YouTubeDownloader_v1.0.3.zip" "YouTubeDownloader_v1.0.3"
    echo "Fichier créé: dist/YouTubeDownloader_v1.0.3.zip"
else
    # Linux: tar.gz
    tar -czvf "YouTubeDownloader_v1.0.3.tar.gz" "YouTubeDownloader_v1.0.3"
    echo "Fichier créé: dist/YouTubeDownloader_v1.0.3.tar.gz"
fi
cd ..

echo ""
echo "==================================================="
echo "    COMPILATION TERMINEE !"
echo "==================================================="
echo ""
echo "L'exécutable se trouve dans le dossier 'dist'."
echo ""
