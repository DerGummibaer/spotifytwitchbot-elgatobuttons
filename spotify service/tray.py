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

        log.info("Downloaded update to %s, launching silent install", installer_path)
        _notify(icon, "Installing update", f"Installing v{latest} in the background. The tray icon will restart shortly.")
        _launch_silent_install(installer_path)

        # Give the installer's [Code] section a moment to start before we
        # exit -- the installer can't overwrite files this process still
        # has open, so we close down right after handing off. This must
        # stop both the tray icon's main-thread loop (icon.stop()) and the
        # asyncio service loop, the same as the Exit menu item does --
        # otherwise the process keeps running and holds the exe file open,
        # which would make the installer's file overwrite fail silently.
        def _shutdown_for_update():
            if _tray_icon:
                _tray_icon.stop()
            if _on_exit:
                _on_exit()

        threading.Timer(2.0, _shutdown_for_update).start()

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
    Launches the downloaded installer with fully silent flags, as a
    detached process that survives this one exiting. /VERYSILENT and
    /SUPPRESSMSGBOXES together mean no UI at all and no message boxes
    even on error; /NORESTART prevents an unexpected reboot.
    """
    subprocess.Popen(
        [installer_path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
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
