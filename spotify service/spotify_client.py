"""
Thin wrapper around spotipy. Run this file directly once, the first time,
to complete the one-time browser login and create the local token cache.
After that, the bot imports SpotifyController and it refreshes silently.
"""
import logging

import spotipy
from spotipy.oauth2 import SpotifyPKCE

import config

log = logging.getLogger("spotify")


class SpotifyController:
    def __init__(self):
        self.auth_manager = SpotifyPKCE(
            client_id=config.SPOTIFY_CLIENT_ID,
            redirect_uri=config.SPOTIFY_REDIRECT_URI,
            scope=config.SPOTIFY_SCOPES,
            cache_path=config.SPOTIFY_TOKEN_CACHE,
        )
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)

    def _active_device_id(self):
        """Find the currently active device, if any. Returns None if nothing is playing."""
        devices = self.sp.devices()
        for d in devices.get("devices", []):
            if d.get("is_active"):
                return d["id"]
        # fall back to the first available device if nothing is marked active
        if devices.get("devices"):
            return devices["devices"][0]["id"]
        return None

    def get_volume(self) -> int | None:
        playback = self.sp.current_playback()
        if not playback or not playback.get("device"):
            return None
        return playback["device"]["volume_percent"]

    def set_volume(self, percent: int) -> bool:
        percent = max(0, min(100, percent))
        device_id = self._active_device_id()
        if device_id is None:
            log.warning("set_volume: no active Spotify device found")
            return False
        self.sp.volume(percent, device_id=device_id)
        return True

    def adjust_volume(self, delta: int) -> int | None:
        """Used by Stream Deck vol_up/vol_down. Returns the new volume, or None on failure."""
        current = self.get_volume()
        if current is None:
            return None
        new_volume = max(0, min(100, current + delta))
        if self.set_volume(new_volume):
            return new_volume
        return None

    def skip(self) -> bool:
        device_id = self._active_device_id()
        if device_id is None:
            return False
        self.sp.next_track(device_id=device_id)
        return True

    def previous(self) -> bool:
        device_id = self._active_device_id()
        if device_id is None:
            return False
        self.sp.previous_track(device_id=device_id)
        return True

    def get_playback_state(self) -> dict:
        """Returns current track info, play state, and album art URL, for
        things like a Stream Deck button that displays the now-playing song."""
        playback = self.sp.current_playback()
        if not playback or not playback.get("item"):
            return {"is_playing": False, "track": None, "artist": None, "album_art_url": None}
        item = playback["item"]
        artists = item.get("artists", [])
        images = item.get("album", {}).get("images", [])
        # Spotify returns images sorted largest-first; a mid-size one (usually
        # the second entry, ~300px) is plenty for a Stream Deck key and keeps
        # the download small. Falls back to the first available if only one exists.
        album_art_url = None
        if images:
            album_art_url = images[1]["url"] if len(images) > 1 else images[0]["url"]
        return {
            "is_playing": playback.get("is_playing", False),
            "track": item.get("name"),
            "artist": artists[0]["name"] if artists else None,
            "album_art_url": album_art_url,
            "uri": item.get("uri"),
        }

    def play_pause(self) -> bool:
        """Toggles playback. Returns True on success."""
        device_id = self._active_device_id()
        if device_id is None:
            return False
        state = self.get_playback_state()
        if state["is_playing"]:
            self.sp.pause_playback(device_id=device_id)
        else:
            self.sp.start_playback(device_id=device_id)
        return True

    def search_track(self, query: str) -> dict | None:
        """Search by free text. Returns a simplified track dict, or None if no match."""
        results = self.sp.search(q=query, type="track", limit=1)
        items = results.get("tracks", {}).get("items", [])
        if not items:
            return None
        track = items[0]
        return {
            "uri": track["uri"],
            "name": track["name"],
            "artist": track["artists"][0]["name"] if track["artists"] else "Unknown",
        }

    def resolve_track(self, song_or_link: str) -> dict | None:
        """Accepts either a Spotify URL/URI or a free-text search query."""
        text = song_or_link.strip()
        if "open.spotify.com/track/" in text:
            track_id = text.split("track/")[1].split("?")[0]
            uri = f"spotify:track:{track_id}"
        elif text.startswith("spotify:track:"):
            uri = text
        else:
            return self.search_track(text)

        track = self.sp.track(uri)
        return {
            "uri": track["uri"],
            "name": track["name"],
            "artist": track["artists"][0]["name"] if track["artists"] else "Unknown",
        }

    def queue_add(self, song_or_link: str) -> dict | None:
        """Resolves and adds a track to the queue. Returns track info on success, None on failure."""
        track = self.resolve_track(song_or_link)
        if track is None:
            return None
        device_id = self._active_device_id()
        if device_id is None:
            log.warning("queue_add: no active Spotify device found")
            return None
        self.sp.add_to_queue(track["uri"], device_id=device_id)
        return track

    def get_queue(self, limit: int = 5) -> list[dict]:
        queue = self.sp.queue()
        items = queue.get("queue", [])[:limit]
        return [
            {"name": t["name"], "artist": t["artists"][0]["name"] if t["artists"] else "Unknown"}
            for t in items
        ]

    def get_playlists(self, limit: int = 50) -> list[dict]:
        """Returns the current user's playlists as {id, name}, for populating
        the Stream Deck property inspector's playlist dropdown."""
        results = self.sp.current_user_playlists(limit=limit)
        return [{"id": p["id"], "name": p["name"]} for p in results.get("items", [])]

    def add_current_track_to_playlist(self, playlist_id: str) -> dict | None:
        """Adds the currently playing track to the given playlist. Returns
        track info on success (for showing feedback), or None if nothing
        is currently playing or the add failed."""
        playback = self.sp.current_playback()
        if not playback or not playback.get("item"):
            return None
        track = playback["item"]
        try:
            self.sp.playlist_add_items(playlist_id, [track["uri"]])
        except Exception as e:
            log.warning(f"Failed to add track to playlist: {e}")
            return None
        artists = track.get("artists", [])
        return {
            "name": track.get("name"),
            "artist": artists[0]["name"] if artists else "Unknown",
        }


if __name__ == "__main__":
    # Run this file directly the first time to do the one-time browser login.
    # A browser window opens; log in and approve. After that the refresh
    # token is cached locally and the bot will not prompt again.
    logging.basicConfig(level=logging.INFO)
    controller = SpotifyController()
    vol = controller.get_volume()
    print(f"Connected. Current volume: {vol}")
