"""
The always-on Spotify service. Runs as a system tray icon (right-click
to re-authorize, check for updates, or exit). The control socket for
Stream Deck and the Twitch bot runs in a background thread.
"""
import asyncio
import logging
import os
import sys
import threading

import config
import tray
from control_server import ControlServer
from spotify_client import SpotifyController

os.makedirs(config.LOG_DIR, exist_ok=True)

handlers = [logging.FileHandler(os.path.join(config.LOG_DIR, config.LOG_FILE))]
if sys.stdout is not None:
    handlers.append(logging.StreamHandler())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=handlers,
)

log = logging.getLogger("main")

# Global references shared between the main thread (tray) and the
# service thread (asyncio loop + control server).
_spotify: SpotifyController | None = None
_loop: asyncio.AbstractEventLoop | None = None
_shutdown_event: asyncio.Event | None = None


def _build_spotify() -> SpotifyController:
    """Creates a fresh SpotifyController. Called at startup and on re-auth."""
    return SpotifyController()


def _poll_now_playing():
    """
    Background task that updates the tray icon with the currently playing
    track every 10 seconds, and marks the tray disconnected on error.
    """
    async def _run():
        while True:
            try:
                state = _spotify.get_playback_state()
                if state.get("track"):
                    tray.set_connected(f"{state['track']} — {state.get('artist', '')}")
                else:
                    tray.set_connected(None)
            except Exception as e:
                log.warning("Spotify poll failed: %s", e)
                tray.set_disconnected(str(e)[:60])
            await asyncio.sleep(10)
    return _run()


def _service_thread_main():
    """
    Runs in a background thread. Owns the asyncio event loop, the control
    server, and the now-playing poll loop.
    """
    global _spotify, _loop, _shutdown_event

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _loop = loop
    _shutdown_event = asyncio.Event()

    try:
        _spotify = _build_spotify()
        vol = _spotify.get_volume()
        log.info(f"Spotify connected. Current volume: {vol}")
        tray.set_connected()

        control_server = ControlServer(_spotify)

        async def _run_all():
            poll_task = loop.create_task(_poll_now_playing())
            server_task = loop.create_task(control_server.start())
            await _shutdown_event.wait()
            poll_task.cancel()
            server_task.cancel()

        loop.run_until_complete(_run_all())
    except Exception as e:
        log.exception("Service thread failed")
        tray.set_disconnected(str(e)[:60])
    finally:
        loop.close()


def _reauth():
    """
    Called by the tray's Re-authorize menu item. Deletes the cached token
    so the next SpotifyController init triggers the browser flow again,
    then restarts the controller. Runs in a daemon thread.
    """
    global _spotify

    log.info("Re-authorization requested")
    tray.set_disconnected("Re-authorizing...")

    # Delete the cached token so spotipy triggers the browser flow.
    try:
        if os.path.exists(config.SPOTIFY_TOKEN_CACHE):
            os.remove(config.SPOTIFY_TOKEN_CACHE)
            log.info("Deleted cached token for re-auth")
    except OSError as e:
        log.warning("Could not delete token cache: %s", e)

    # Rebuild the controller -- this opens a browser window for login.
    try:
        _spotify = _build_spotify()
        log.info("Re-authorization complete")
        tray.set_connected()
    except Exception as e:
        log.exception("Re-authorization failed")
        tray.set_disconnected(f"Re-auth failed: {str(e)[:40]}")


def _exit():
    """Called by the tray's Exit menu item."""
    log.info("Exit requested")
    if _loop and _shutdown_event:
        _loop.call_soon_threadsafe(_shutdown_event.set)


def _setup(icon_instance=None):
    """Called by pystray once the tray icon is ready. Starts the service thread."""
    tray.register_callbacks(on_reauth=_reauth, on_exit=_exit)
    thread = threading.Thread(target=_service_thread_main, daemon=True, name="service")
    thread.start()


if __name__ == "__main__":
    tray.run_tray(setup_callback=_setup)
