@echo off
REM Builds and packages the Stream Deck plugin from this folder's source.
REM Produces com.leon.spotifycontrol.streamDeckPlugin in this same folder.

cd /d %~dp0

echo ===============================================
echo  Spotify Stream Deck Plugin - Build
echo ===============================================
echo.

echo Installing/updating dependencies...
call npm install
if errorlevel 1 (
    echo.
    echo FAILED: npm install failed. See the error above.
    pause
    exit /b 1
)

echo.
echo Compiling TypeScript...
call npm run build
if errorlevel 1 (
    echo.
    echo FAILED: npm run build failed. See the error above.
    echo If this is a TypeScript error, paste the exact message back
    echo to fix the source.
    pause
    exit /b 1
)

echo.
echo Packaging plugin...
call streamdeck pack com.leon.spotifycontrol.sdPlugin
if errorlevel 1 (
    echo.
    echo FAILED: streamdeck pack failed. Is the Stream Deck CLI installed?
    echo Install it with: npm install -g @elgato/cli
    pause
    exit /b 1
)

echo.
echo ===============================================
echo  Build complete!
echo  Output: com.leon.spotifycontrol.streamDeckPlugin
echo ===============================================
echo.
echo Double-click that file to install/update the plugin in Stream Deck.
echo.
pause
