# Installer

Builds a single `SpotifyStreamDeckSuiteSetup.exe` that installs:
- the always-on Spotify service (required)
- the Twitch chat bot (optional, checkbox during install)
- triggers installing the Stream Deck plugin
- adds a Startup folder shortcut so the Spotify service starts at login
- collects Spotify and Twitch credentials interactively and writes the
  `.env` files for both programs automatically
- supports silent self-update (see SILENT UPDATE SUPPORT comment at the
  top of `SpotifyStreamDeckSuite.iss`)

## What you need before compiling

See `payload\README.txt` for the exact files this expects and how to
produce them (PyInstaller builds of the two Python programs, plus the
packaged Stream Deck plugin file).

## Compiling

1. Install Inno Setup: https://jrsoftware.org/isdl.php
2. Make sure `payload\` is filled in correctly (see `payload\README.txt`)
3. Open `SpotifyStreamDeckSuite.iss` in Inno Setup
4. Build → Compile (or Ctrl+F9)
5. Find the result in `output\SpotifyStreamDeckSuiteSetup.exe`

## What the installer actually does, step by step

1. Standard welcome / license / install location screens (installs to
   `%LOCALAPPDATA%\Spotify Stream Deck Suite` by default, no admin needed)
2. Component selection (Twitch bot on/off)
3. Custom page: asks for the Spotify Client ID, with inline instructions
   for creating a Spotify app
4. Custom page: asks for Twitch credentials -- skipped entirely if the
   Twitch bot component wasn't selected
5. Copies the program files
6. Generates `.env` for the Spotify service (always) and the Twitch bot
   (if selected), from what was entered in steps 3-4
7. Adds a shortcut to the current user's Startup folder so the Spotify
   service launches automatically at every login -- no admin/elevation
   needed for this, unlike a Task Scheduler entry
8. Launches the Spotify service immediately so the one-time browser
   login can happen right away, with on-screen guidance
9. On the finish screen, offers to install the Stream Deck plugin (opens
   the `.streamDeckPlugin` file) and to open the OBS Autostarter download
   page (only relevant if the Twitch bot was installed and you want it
   tied to OBS specifically)

## Limitations to know about

- **OBS Autostarter itself is not installed by this installer.** It's a
  third-party OBS plugin; this installer can only open its download page
  and leave the rest to the user, since silently modifying another
  program's plugin folder isn't something it's safe or appropriate to do.
- **No administrator privileges required**
  (`PrivilegesRequired=lowest` in the script). The install goes to
  `%LOCALAPPDATA%`, which the current user already owns, and autostart
  uses a Startup folder shortcut rather than Task Scheduler -- on at
  least some Windows configurations, `schtasks.exe` denies even per-user
  `/SC ONLOGON` task creation without elevation, which is why Task
  Scheduler was dropped in favor of the Startup folder approach.
- **Startup folder vs. Task Scheduler behavior differs slightly.** A
  Startup folder shortcut runs at desktop login (with a small built-in
  delay on modern Windows) rather than at the exact moment of logon, and
  can be disabled by the user via Task Manager's Startup tab or any
  third-party "startup optimizer" tool. This is an acceptable tradeoff
  for not needing admin rights.
- **Per-user Spotify apps.** Each person who runs this installer needs
  their own free Spotify Client ID -- the wizard links to the right page
  and explains why, but can't skip this step. This is intentional (see
  the project history for why a shared Client ID isn't used).

## Uninstalling

The generated uninstaller (Control Panel → Programs, or the Start Menu
shortcut) removes the installed files and the Startup folder shortcut
automatically, the same as any other icon Inno Setup creates. It does
not attempt to remove the Stream Deck plugin or OBS Autostarter, since
those were installed by separate tools outside this installer's control.
