@echo off
echo ===================================================
echo     COMPILATION DU DOWNLOADER YOUTUBE (HARD)
echo ===================================================
echo.
echo Installation des dependances...
pip install -r requirements.txt
echo.
echo Nettoyage des anciens builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
del /q *.spec
echo.
echo Lancement de PyInstaller pour UPDATER...
python -m PyInstaller --noconfirm --onefile --console --name "updater" updater.py

echo.
echo Lancement de PyInstaller pour MAIN APP...
echo Cela peut prendre quelques minutes...
echo.
python -m PyInstaller --noconfirm --onefile --windowed --name "YouTubeDownloader_v1.0.3" --icon="NONE" --add-data "ffmpeg.exe;." --add-data "dist/updater.exe;." main.py

echo.
echo ===================================================
echo     COMPILATION TERMINEE !
echo ===================================================
echo.
echo L'executable se trouve dans le dossier 'dist'.
echo Vous pouvez copier 'dist\YouTubeDownloader_v1.0.3.exe' ou vous voulez.
echo.
echo NOTE: Pour que la fusion Audio/Video fonctionne en haute qualite (1080p+),
echo vous devez avoir 'ffmpeg.exe' dans le meme dossier que l'application
echo ou installe dans votre systeme.
echo.
echo.
