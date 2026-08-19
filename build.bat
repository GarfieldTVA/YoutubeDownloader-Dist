@echo off
setlocal

echo ===================================================
echo   BUILD YouTube Downloader Ultimate v1.1.0
echo ===================================================

echo [1/4] Installation / mise a jour des dependances...
python -m pip install --upgrade pip
python -m pip install --upgrade --pre -r requirements.txt
if %errorlevel% neq 0 exit /b %errorlevel%

echo [2/4] Nettoyage...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
for %%F in (*.spec) do del /q "%%F"

echo [3/4] Compilation de l'updater...
python -m PyInstaller --noconfirm --clean --onefile --console --name "updater" updater.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo [4/4] Compilation de l'application...
set EXTRA_BIN=
if exist ffmpeg.exe set EXTRA_BIN=%EXTRA_BIN% --add-binary "ffmpeg.exe;."
if exist ffplay.exe set EXTRA_BIN=%EXTRA_BIN% --add-binary "ffplay.exe;."

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "YouTubeDownloader_v1.1.0" ^
  --add-binary "dist/updater.exe;." ^
  %EXTRA_BIN% ^
  main.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo.
echo Build termine : dist\YouTubeDownloader_v1.1.0.exe
endlocal
