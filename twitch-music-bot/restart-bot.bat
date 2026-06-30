@echo off
REM Restarts TwitchMusicBot.exe -- run this after editing
REM command_aliases.txt (or any other .env/config change) so the new
REM settings actually take effect, since they're only read at startup.
REM
REM Place this file directly in the TwitchMusicBot install folder,
REM next to TwitchMusicBot.exe itself.

cd /d %~dp0

if not exist "TwitchMusicBot.exe" (
    echo FAILED: TwitchMusicBot.exe not found in this folder.
    echo Make sure this .bat file is sitting next to the exe.
    pause
    exit /b 1
)

echo Stopping TwitchMusicBot.exe if running...
taskkill /IM TwitchMusicBot.exe /F >nul 2>&1

REM Brief pause so the old process fully releases before relaunching --
REM not strictly required here since we're not overwriting the exe, but
REM avoids any chance of two instances racing for the same resources.
ping -n 2 127.0.0.1 >nul

echo Starting TwitchMusicBot.exe...
start "" "TwitchMusicBot.exe"

echo.
echo Done. The bot should reconnect to Twitch chat in a few seconds.
echo Check logs\ if it doesn't seem to come back.
echo.
pause
