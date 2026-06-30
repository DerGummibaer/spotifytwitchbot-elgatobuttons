@echo off
REM Pushes the current state of all four project folders to GitHub.
REM Run this from anywhere -- it cd's to its own folder first.
REM
REM This does NOT create a version tag or GitHub release -- see the
REM separate instructions for that (bump version.py, rebuild everything,
REM then tag and release manually, since attaching the installer .exe to
REM a release isn't something git push can do on its own).

cd /d %~dp0

echo ===============================================
echo  Spotify Stream Deck Suite - Push to GitHub
echo ===============================================
echo.

echo Current status:
git status
echo.

set /p CONFIRM="Does the file list above look correct (no dist/, node_modules/, compiled exes)? [y/n]: "
if /i not "%CONFIRM%"=="y" (
    echo.
    echo Aborted. Check your .gitignore or unstage anything that shouldn't be there.
    pause
    exit /b 1
)

echo.
set /p MSG="Commit message: "
if "%MSG%"=="" (
    echo.
    echo FAILED: commit message cannot be empty.
    pause
    exit /b 1
)

git add .
git commit -m "%MSG%"
if errorlevel 1 (
    echo.
    echo Nothing to commit, or commit failed. See above.
    pause
    exit /b 1
)

echo.
echo Pushing to GitHub...
git push
if errorlevel 1 (
    echo.
    echo FAILED: git push failed. See the error above.
    echo If this is an authentication prompt, complete it in the browser window
    echo that should have opened, then re-run this script.
    pause
    exit /b 1
)

echo.
echo ===============================================
echo  Pushed successfully!
echo ===============================================
echo.
echo Reminder: this did NOT create a version tag or GitHub release.
echo If this is a real release (not just a small fix), also run:
echo.
echo   git tag vX.Y.Z
echo   git push origin vX.Y.Z
echo.
echo Then go to GitHub -^> Releases -^> Create a new release -^> select the
echo tag -^> attach the new SpotifyStreamDeckSuiteSetup.exe -^> publish.
echo.
pause
