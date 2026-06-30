"""
System tray icon for the Spotify service. Runs on the main thread
(pystray requirement). The asyncio service loop runs in a background
thread and communicates back here via thread-safe state updates.
"""
import logging
import os
import subprocess
import tempfile
import threading
import urllib.request
import urllib.error
import json
import webbrowser

import pystray
from PIL import Image, ImageDraw

from version import VERSION

log = logging.getLogger("tray")

GITHUB_REPO = "DerGummibaer/spotifytwitchbot-elgatobuttons"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Shared state -- written by the service thread, read by tray menu callbacks.
_state = {
    "connected": False,
    "track": None,
    "error": None,
}
_state_lock = threading.Lock()

# Callbacks registered by main.py so the tray can trigger re-auth / shutdown.
_on_reauth = None
_on_exit = None
_tray_icon = None


def register_callbacks(on_reauth, on_exit):
    global _on_reauth, _on_exit
    _on_reauth = on_reauth
    _on_exit = on_exit


def set_connected(track: str | None = None):
    with _state_lock:
        _state["connected"] = True
        _state["track"] = track
        _state["error"] = None
    _refresh_icon()


def set_disconnected(error: str | None = None):
    with _state_lock:
        _state["connected"] = False
        _state["track"] = None
        _state["error"] = error
    _refresh_icon()


def _make_icon_image(connected: bool) -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = (100, 65, 165) if connected else (120, 120, 120)
    bar = (255, 255, 255)

    # Twitch logo silhouette: rectangle with two diagonal bottom corners cut off
    p = 4
    w = size - p * 2
    body = [
        (p,              p),
        (p + w,          p),
        (p + w,          p + w * 0.72),
        (p + w * 0.72,   p + w),
        (p + w * 0.28,   p + w),
        (p,              p + w * 0.72),
    ]
    draw.polygon(body, fill=color)

    # Two vertical white bars (the Twitch logo detail)
    bw = round(w * 0.10)
    bh = round(w * 0.38)
    by = round(p + w * 0.18)

    lx = round(p + w * 0.26)
    draw.rectangle([lx, by, lx + bw, by + bh], fill=bar)

    rx = round(p + w * 0.52)
    draw.rectangle([rx, by, rx + bw, by + bh], fill=bar)

    return img


def _refresh_icon():
    global _tray_icon
    if _tray_icon is None:
        return
    with _state_lock:
        connected = _state["connected"]
        track = _state["track"]
        error = _state["error"]

    _tray_icon.icon = _make_icon_image(connected)

    if connected and track:
        _tray_icon.title = f"Spotify: {track}"
    elif connected:
        _tray_icon.title = "Spotify service: connected"
    elif error:
        _tray_icon.title = f"Spotify service: {error}"
    else:
        _tray_icon.title = "Spotify service: disconnected"

    _tray_icon.update_menu()


def _kill_twitch_bot_if_running() -> bool:
    """
    Stops TwitchMusicBot.exe before a silent update, if it's running.
    Returns True if a running process was actually found and stopped,
    False if it wasn't running at all (so the installer knows whether to
    relaunch it afterward -- only if it was actually running before).

    The Twitch bot is a separate process from this service, often
    launched independently by OBS Autostarter, and the silent update
    flow had no awareness of it at all -- only this service's own exe
    was ever stopped before handing off to the installer. If the bot
    component is installed and happened to be running (e.g. OBS was
    open), its exe would still be locked when the installer reached its
    [Files] copy step for TwitchMusicBot.exe, causing exactly the same
    silent skip-the-locked-file failure we already fixed for
    SpotifyService.exe itself, but for the bot instead.

    taskkill /IM /F on a process that isn't running just fails harmlessly
    (exit code 128, "process not found") -- we don't treat that as an
    error, since most users either don't have the bot installed at all,
    or simply aren't running it at update time.
    """
    try:
        result = subprocess.run(
            ["taskkill", "/IM", "TwitchMusicBot.exe", "/F"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            log.info("Stopped TwitchMusicBot.exe before silent update")
            return True
        # else: not running, or already stopped -- nothing to log, this
        # is the common case for most users.
        return False
    except Exception as e:
        log.warning("Could not check/stop TwitchMusicBot.exe: %s", e)
        return False


def _write_bot_was_running_marker():
    """
    Writes a small marker file the installer checks for (in its update
    path) to know whether to relaunch the Twitch bot after a silent
    update -- only if it was actually running before we stopped it,
    rather than launching it for everyone who merely has it installed.
    Lives in the TwitchMusicBot folder itself, alongside .env, so both
    this service and the separate installer process agree on the path
    without needing any other communication channel between them.
    """
    try:
        import config
        marker_path = os.path.normpath(
            os.path.join(config.base_dir, "..", "TwitchMusicBot", "_was_running_before_update")
        )
        with open(marker_path, "w") as f:
            f.write("")
        log.info("Wrote bot-was-running marker at %s", marker_path)
    except Exception as e:
        log.warning("Could not write bot-was-running marker: %s", e)


def _check_for_updates(icon, item):
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"User-Agent": f"spotifytwitchbot-elgatobuttons/{VERSION}"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        latest = data.get("tag_name", "").lstrip("v")
        if not latest:
            _notify(icon, "Update check", "Could not determine latest version.")
            return
        if not _version_gt(latest, VERSION):
            _notify(icon, "Up to date", f"You're running the latest version (v{VERSION}).")
            return

        asset_url = _find_installer_asset_url(data)
        if asset_url is None:
            log.warning("No installer asset found in release v%s, falling back to browser", latest)
            _notify(icon, "Update available", f"v{latest} is available. Opening releases page...")
            webbrowser.open(GITHUB_RELEASES_URL)
            return

        _notify(icon, "Downloading update", f"Downloading v{latest}, this will only take a moment...")
        installer_path = _download_installer(asset_url)
        if installer_path is None:
            _notify(icon, "Update failed", "Could not download the update. Opening releases page instead...")
            webbrowser.open(GITHUB_RELEASES_URL)
            return

        log.info("Downloaded update to %s, scheduling delayed silent install", installer_path)
        _notify(icon, "Installing update", f"Installing v{latest} in the background. The tray icon will restart shortly.")

        # Stop the Twitch bot first if it's running (e.g. via OBS
        # Autostarter) -- its exe needs to be unlocked for the
        # installer's [Files] step too, the same as this service's own
        # exe. This must happen before _launch_silent_install schedules
        # the installer, giving it a head start on actually being gone.
        # If it WAS running, write a marker file the installer (a
        # separate process with no other way to know this) can check for
        # to know whether to relaunch the bot afterward.
        bot_was_running = _kill_twitch_bot_if_running()
        if bot_was_running:
            _write_bot_was_running_marker()

        _launch_silent_install(installer_path)

        # Exit immediately and unconditionally -- the delay before the
        # installer actually runs is now handled entirely inside the
        # detached wrapper process from _launch_silent_install, not by
        # timing our own shutdown against it. This must stop both the
        # tray icon's main-thread loop (icon.stop()) and the asyncio
        # service loop, the same as the Exit menu item does -- otherwise
        # the process keeps running and holds the exe file open well
        # past when the wrapper's timeout elapses, which would have us
        # right back in the same race we just fixed.
        if _tray_icon:
            _tray_icon.stop()
        if _on_exit:
            _on_exit()

    except Exception as e:
        log.warning("Update check failed: %s", e)
        _notify(icon, "Update check failed", "Could not reach GitHub. Check your connection.")


def _find_installer_asset_url(release_data: dict) -> str | None:
    """Looks through a GitHub release's assets for the Setup.exe installer."""
    for asset in release_data.get("assets", []):
        name = asset.get("name", "")
        if name.lower().endswith(".exe") and "setup" in name.lower():
            return asset.get("browser_download_url")
    return None


def _download_installer(url: str) -> str | None:
    """Downloads the installer exe to a temp path. Returns the local path,
    or None on failure."""
    try:
        temp_dir = tempfile.gettempdir()
        local_path = os.path.join(temp_dir, "SpotifyStreamDeckSuiteSetup_update.exe")
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"spotifytwitchbot-elgatobuttons/{VERSION}"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(local_path, "wb") as f:
            f.write(data)
        return local_path
    except Exception as e:
        log.warning("Failed to download installer: %s", e)
        return None


def _launch_silent_install(installer_path: str):
    """
    Launches the downloaded installer with fully silent flags, delayed by
    a few seconds, via a small generated .bat file run as a detached
    process -- NOT launched directly, and NOT via a hand-built `cmd /c
    "..."` command-line string.

    This matters for two separate reasons:

    1. The installer needs to overwrite SpotifyService.exe, which is
       still open and locked by THIS running process at the moment this
       function is called. Launching the installer directly and then
       separately scheduling our own shutdown a couple seconds later is
       a race -- there's no guarantee our process (and its file lock) is
       actually gone by the time the installer reaches its file-copy
       step. On a real test this race was lost: the installer ran,
       "succeeded", but silently skipped overwriting the locked exe.

    2. The first fix for that used `cmd /c "timeout ... & ""path"" ..."`
       as a single command-line string passed to Popen with shell=True.
       That also failed silently on a real test -- cmd.exe has a
       well-documented quirk where, if a command passed to /c begins
       with a quote character, it strips only the OUTER matching quote
       pair and does not re-parse what's left normally. With our
       embedded quoted installer path sitting inside an outer quoted
       string, this is exactly the ambiguous nested-quoting situation
       that trips up cmd.exe's parser, and it can fail with no visible
       error at all since everything here is detached and silent.

    The fix for both: write a small standalone .bat file to a temp path,
    where each line is parsed normally by cmd.exe (no nested-quoting
    ambiguity, since we're not cramming everything into one /c string),
    and launch THAT file as the detached process instead.

    3. Even after fix #2, this STILL failed silently on a real test on a
       different PC -- the .bat file was correctly written to disk, but
       double-clicking it manually showed a console window flash and
       close immediately, with no installer ever launching. Root cause:
       the "timeout" command requires a console input stream to listen
       for a keypress that could interrupt the wait, and this .bat runs
       as a fully detached background process with NO console attached
       at all -- so timeout doesn't wait, it fails INSTANTLY with
       "ERROR: Input redirection is not supported, exiting the process
       immediately" and the script moves on right away. This is a
       well-documented Windows quirk specific to "timeout" in background/
       non-interactive contexts; "ping -n N 127.0.0.1" is the standard
       workaround, since ping needs no console input and is present on
       every Windows install by default.
    """
    delay_seconds = 3
    bat_path = os.path.join(tempfile.gettempdir(), "spotify_suite_update.bat")
    bat_contents = (
        "@echo off\n"
        # NOT "timeout /t N" -- timeout tries to listen for a keypress to
        # interrupt the wait, which requires a console input stream. This
        # .bat is launched as a fully detached background process with no
        # console attached at all, so timeout fails INSTANTLY with
        # "ERROR: Input redirection is not supported, exiting the process
        # immediately" rather than actually waiting -- confirmed as the
        # real cause on a real test, where the .bat visibly flashed and
        # closed immediately instead of waiting 3 seconds. Pinging the
        # loopback address is the standard, well-documented workaround:
        # ping doesn't need console input, and is present on every
        # Windows install by default. -n {delay_seconds + 1} sends one
        # extra ping because the first one fires immediately rather than
        # after a delay, so N+1 pings ~1 second apart give N seconds of
        # actual waiting.
        f"ping -n {delay_seconds + 1} 127.0.0.1 >nul\n"
        f'"{installer_path}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART\n'
    )
    with open(bat_path, "w") as f:
        f.write(bat_contents)

    subprocess.Popen(
        [bat_path],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )


def _version_gt(a: str, b: str) -> bool:
    """Returns True if version string a is greater than b (simple semver)."""
    try:
        return tuple(int(x) for x in a.split(".")) > tuple(int(x) for x in b.split("."))
    except ValueError:
        return False


def _notify(icon, title: str, message: str):
    """Show a system tray notification if the platform supports it."""
    try:
        icon.notify(message, title)
    except Exception:
        log.info("%s: %s", title, message)


def _reauth(icon, item):
    if _on_reauth:
        threading.Thread(target=_on_reauth, daemon=True).start()


def _open_log(icon, item):
    import config
    log_path = os.path.join(config.LOG_DIR, config.LOG_FILE)
    os.startfile(log_path)


def _exit(icon, item):
    icon.stop()
    if _on_exit:
        _on_exit()


def _build_menu():
    with _state_lock:
        connected = _state["connected"]
        track = _state["track"]
        error = _state["error"]

    if connected and track:
        status_text = f"Now playing: {track}"
    elif connected:
        status_text = "Connected to Spotify"
    elif error:
        status_text = f"Error: {error}"
    else:
        status_text = "Not connected"

    return pystray.Menu(
        pystray.MenuItem(status_text, None, enabled=False),
        pystray.MenuItem(f"Version {VERSION}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Re-authorize Spotify", _reauth),
        pystray.MenuItem("Check for updates", _check_for_updates),
        pystray.MenuItem("Open log file", _open_log),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", _exit),
    )


def run_tray(setup_callback):
    """
    Creates and runs the tray icon. Blocking -- call from the main thread.
    setup_callback is called in a background thread once the icon is ready;
    put the asyncio service startup there.
    """
    global _tray_icon

    icon = pystray.Icon(
        name="SpotifyService",
        icon=_make_icon_image(False),
        title="Spotify service: starting...",
        menu=pystray.Menu(_build_menu),
    )
    _tray_icon = icon

    def _setup(i):
        i.visible = True
        setup_callback()

    icon.run(setup=_setup)
