@echo off
REM Reads the current version number from version.ini (kept in sync with
REM version.py by rebuild-all.bat) and creates + pushes a matching git tag,
REM so you never have to type the version number by hand or risk a typo
REM mismatch between the tag and what's actually in the version files.

cd /d %~dp0

set VERSION_INI="spotify service\version.ini"

if not exist %VERSION_INI% (
    echo FAILED: could not find %VERSION_INI%
    echo Are you running this from the project root, next to the four project folders?
    pause
    exit /b 1
)

REM Pull the value after "Number=" on the line that starts with it.
REM /f tokens=2 delims== splits "Number=1.2.1" into token 1 "Number" and
REM token 2 "1.2.1" using "=" as the delimiter.
for /f "usebackq tokens=2 delims==" %%V in (`findstr /b "Number=" %VERSION_INI%`) do set CURRENT_VERSION=%%V

if "%CURRENT_VERSION%"=="" (
    echo FAILED: could not find a "Number=" line in %VERSION_INI%
    pause
    exit /b 1
)

echo ===============================================
echo  Tag and Release
echo ===============================================
echo.
echo Current version in version.ini: %CURRENT_VERSION%
echo This will create tag: v%CURRENT_VERSION%
echo.

set /p CONFIRM="Create and push this tag now? [y/n]: "
if /i not "%CONFIRM%"=="y" (
    echo.
    echo Cancelled. No tag was created.
    pause
    exit /b 0
)

echo.
git tag v%CURRENT_VERSION%
if errorlevel 1 (
    echo.
    echo FAILED: git tag failed. If this tag already exists, you'll need to
    echo bump the version number first ^(run rebuild-all.bat^) or delete the
    echo old tag manually if this was a mistake: git tag -d v%CURRENT_VERSION%
    pause
    exit /b 1
)

git push origin v%CURRENT_VERSION%
if errorlevel 1 (
    echo.
    echo FAILED: git push failed. The local tag was created but not pushed --
    echo you can retry with: git push origin v%CURRENT_VERSION%
    pause
    exit /b 1
)

echo.
echo ===============================================
echo  Tag v%CURRENT_VERSION% pushed!
echo ===============================================
echo.
echo Next: go to GitHub -^> Releases -^> Create a new release -^> select the
echo v%CURRENT_VERSION% tag -^> attach the new SpotifyStreamDeckSuiteSetup.exe
echo from Installer\output\ -^> publish.
echo.
echo Reminder: the tray icon's "Check for updates" matches against the
echo release's tag_name, so the GitHub release must actually be published
echo (not left as a draft) for existing installs to detect it.
echo.
pause
