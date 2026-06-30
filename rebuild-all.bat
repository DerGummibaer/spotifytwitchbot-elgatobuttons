@echo off
REM Full rebuild pipeline: cleans old build output for all three projects,
REM rebuilds each from current source, then copies the fresh output into
REM Installer\payload\ so the next Inno Setup compile picks up the latest
REM exes -- this is the exact fix for the "stale exe" bug we kept hitting.
REM
REM Runs straight through with no pauses between steps; only stops and
REM waits if a step actually fails, so you can read the error.
REM
REM Place this file directly in the project root, next to the four
REM project folders (spotify service, twitch-music-bot, spotify-streamdeck,
REM Installer). Run it by double-clicking.

cd /d %~dp0

echo ===============================================
echo  Full Rebuild Pipeline
echo ===============================================
echo.

set /p NEWVERSION="Enter the version number for this build (e.g. 1.2.0), or press Enter to keep the current version: "

if not "%NEWVERSION%"=="" (
    echo.
    echo Updating version.py and version.ini to %NEWVERSION%...
    python "%~dp0set-version.py" "%NEWVERSION%"
    if errorlevel 1 (
        echo.
        echo FAILED: could not update version files. See above.
        pause
        exit /b 1
    )
    echo Done.
)
echo.

REM ---------------------------------------------------------------
REM 1. Spotify Service
REM ---------------------------------------------------------------
echo [1/3] Spotify Service
echo -----------------------------------------------

if exist "spotify service\dist" rmdir /s /q "spotify service\dist"
if exist "spotify service\build" rmdir /s /q "spotify service\build"

pushd "spotify service"
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    popd
    echo.
    echo FAILED: pip install failed for spotify-service. See above.
    pause
    exit /b 1
)
echo Building exe...
pyinstaller SpotifyService.spec
if errorlevel 1 (
    popd
    echo.
    echo FAILED: PyInstaller build failed for spotify-service. See above.
    pause
    exit /b 1
)
popd

if not exist "spotify service\dist\SpotifyService\SpotifyService.exe" (
    echo.
    echo FAILED: SpotifyService.exe was not produced.
    pause
    exit /b 1
)

echo Copying into Installer\payload...
if exist "Installer\payload\SpotifyService" rmdir /s /q "Installer\payload\SpotifyService"
mkdir "Installer\payload\SpotifyService"
xcopy "spotify service\dist\SpotifyService\*" "Installer\payload\SpotifyService\" /e /i /y >nul
echo [1/3] Done.
echo.

REM ---------------------------------------------------------------
REM 2. Twitch Music Bot
REM ---------------------------------------------------------------
echo [2/3] Twitch Music Bot
echo -----------------------------------------------

if exist "twitch-music-bot\dist" rmdir /s /q "twitch-music-bot\dist"
if exist "twitch-music-bot\build" rmdir /s /q "twitch-music-bot\build"

pushd "twitch-music-bot"
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    popd
    echo.
    echo FAILED: pip install failed for twitch-music-bot. See above.
    pause
    exit /b 1
)
echo Building exe...
pyinstaller --name TwitchMusicBot --windowed --onedir main.py
if errorlevel 1 (
    popd
    echo.
    echo FAILED: PyInstaller build failed for twitch-music-bot. See above.
    pause
    exit /b 1
)
popd

if not exist "twitch-music-bot\dist\TwitchMusicBot\TwitchMusicBot.exe" (
    echo.
    echo FAILED: TwitchMusicBot.exe was not produced.
    pause
    exit /b 1
)

echo Copying into Installer\payload...
if exist "Installer\payload\TwitchMusicBot" rmdir /s /q "Installer\payload\TwitchMusicBot"
mkdir "Installer\payload\TwitchMusicBot"
xcopy "twitch-music-bot\dist\TwitchMusicBot\*" "Installer\payload\TwitchMusicBot\" /e /i /y >nul
echo [2/3] Done.
echo.

REM ---------------------------------------------------------------
REM 3. Stream Deck Plugin
REM ---------------------------------------------------------------
echo [3/3] Stream Deck Plugin
echo -----------------------------------------------

if exist "spotify-streamdeck\com.leon.spotifycontrol.sdPlugin\bin" rmdir /s /q "spotify-streamdeck\com.leon.spotifycontrol.sdPlugin\bin"
if exist "spotify-streamdeck\com.leon.spotifycontrol.streamDeckPlugin" del /q "spotify-streamdeck\com.leon.spotifycontrol.streamDeckPlugin"

pushd "spotify-streamdeck"
echo Installing dependencies...
call npm install
if errorlevel 1 (
    popd
    echo.
    echo FAILED: npm install failed for spotify-streamdeck. See above.
    pause
    exit /b 1
)
echo Compiling TypeScript...
call npm run build
if errorlevel 1 (
    popd
    echo.
    echo FAILED: npm run build failed for spotify-streamdeck. See above.
    pause
    exit /b 1
)
echo Packaging plugin...
call streamdeck pack com.leon.spotifycontrol.sdPlugin
if errorlevel 1 (
    popd
    echo.
    echo FAILED: streamdeck pack failed. Is the Stream Deck CLI installed?
    echo Install it with: npm install -g @elgato/cli
    pause
    exit /b 1
)
popd

if not exist "spotify-streamdeck\com.leon.spotifycontrol.streamDeckPlugin" (
    echo.
    echo FAILED: com.leon.spotifycontrol.streamDeckPlugin was not produced.
    pause
    exit /b 1
)

echo Copying into Installer\payload...
copy /y "spotify-streamdeck\com.leon.spotifycontrol.streamDeckPlugin" "Installer\payload\com.leon.spotifycontrol.streamDeckPlugin" >nul
echo [3/3] Done.
echo.

echo ===============================================
echo  All three projects rebuilt and copied!
echo ===============================================
echo.
echo Next step: open Installer\SpotifyStreamDeckSuite.iss in Inno Setup
echo and press Ctrl+F9 to compile the final installer.
echo.
pause
