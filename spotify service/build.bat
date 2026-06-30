@echo off
REM Builds SpotifyService.exe from this folder's source.
REM Run this by double-clicking it, or from a terminal -- it cd's to its
REM own folder first so it works no matter where you call it from.

cd /d %~dp0

echo ===============================================
echo  Spotify Service - Build
echo ===============================================
echo.

echo Installing/updating dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo FAILED: pip install failed. See the error above.
    pause
    exit /b 1
)

echo.
echo Building exe with PyInstaller...
pyinstaller SpotifyService.spec
if errorlevel 1 (
    echo.
    echo FAILED: PyInstaller build failed. See the error above.
    pause
    exit /b 1
)

echo.
echo ===============================================
echo  Build complete!
echo  Output: dist\SpotifyService\
echo ===============================================
echo.
echo Reminder: if you changed Spotify scopes (e.g. added playlist support),
echo delete .spotify_cache or use the tray icon's "Re-authorize Spotify"
echo after running the new exe, or playlist-related buttons will fail.
echo.
pause
