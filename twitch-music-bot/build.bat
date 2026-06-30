@echo off
REM Builds TwitchMusicBot.exe from this folder's source.

cd /d %~dp0

echo ===============================================
echo  Twitch Music Bot - Build
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
pyinstaller --name TwitchMusicBot --windowed --onedir main.py
if errorlevel 1 (
    echo.
    echo FAILED: PyInstaller build failed. See the error above.
    pause
    exit /b 1
)

echo.
echo ===============================================
echo  Build complete!
echo  Output: dist\TwitchMusicBot\
echo ===============================================
echo.
pause
