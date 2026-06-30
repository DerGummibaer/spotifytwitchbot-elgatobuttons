"""
The local socket server. Any client -- the Stream Deck plugin, the
(optional) Twitch bot, or anything else -- connects here and sends one
JSON command per line, gets one JSON response back, per connection.

This server is the only thing that talks to Spotify directly. Everything
else is a client of it.
"""
import asyncio
import json
import logging

import config
from spotify_client import SpotifyController

log = logging.getLogger("control_server")


class ControlServer:
    def __init__(self, spotify: SpotifyController):
        self.spotify = spotify

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        response = {"ok": False, "error": "no response generated"}
        try:
            try:
                # Guard against a connection that opens but never sends
                # data -- without this, such a connection sits open
                # forever and slowly leaks sockets over a long session.
                data = await asyncio.wait_for(reader.readline(), timeout=5)
            except asyncio.TimeoutError:
                return
            if not data:
                return
            message = json.loads(data.decode().strip())
            action = message.get("action")
            response = self._dispatch(action, message)
        except (json.JSONDecodeError, UnicodeDecodeError):
            response = {"ok": False, "error": "invalid json"}
        except Exception as e:
            log.exception("control_server error")
            response = {"ok": False, "error": str(e)}
        finally:
            # finally, not sequential calls -- guarantees the socket is
            # actually released even if writing the response itself fails.
            try:
                writer.write((json.dumps(response) + "\n").encode())
                await writer.drain()
            except Exception:
                pass
            writer.close()
            await writer.wait_closed()

    def _dispatch(self, action: str, message: dict) -> dict:
        if action == "vol_up":
            new_vol = self.spotify.adjust_volume(config.VOLUME_STEP)
            return {"ok": new_vol is not None, "volume": new_vol}
        if action == "vol_down":
            new_vol = self.spotify.adjust_volume(-config.VOLUME_STEP)
            return {"ok": new_vol is not None, "volume": new_vol}
        if action == "vol_adjust":
            delta = int(message.get("delta", 0))
            new_vol = self.spotify.adjust_volume(delta)
            return {"ok": new_vol is not None, "volume": new_vol}
        if action == "vol_set":
            value = int(message.get("value", 0))
            ok = self.spotify.set_volume(value)
            return {"ok": ok, "volume": value if ok else None}
        if action == "get_volume":
            vol = self.spotify.get_volume()
            return {"ok": vol is not None, "volume": vol}
        if action == "skip":
            ok = self.spotify.skip()
            return {"ok": ok}
        if action == "previous":
            ok = self.spotify.previous()
            return {"ok": ok}
        if action == "play_pause":
            ok = self.spotify.play_pause()
            return {"ok": ok}
        if action == "now_playing":
            state = self.spotify.get_playback_state()
            return {"ok": True, **state}
        if action == "queue_add":
            # used by the Twitch bot's !sr -- resolves a song name/link and
            # adds it, returning track info so the bot can announce it in chat
            query = message.get("query", "")
            track = self.spotify.queue_add(query)
            if track is None:
                return {"ok": False, "error": "could not find or queue that song"}
            return {"ok": True, **track}
        if action == "get_queue":
            limit = int(message.get("limit", 5))
            queue = self.spotify.get_queue(limit=limit)
            return {"ok": True, "queue": queue}
        if action == "get_playlists":
            playlists = self.spotify.get_playlists()
            return {"ok": True, "playlists": playlists}
        if action == "add_to_playlist":
            playlist_id = message.get("playlist_id", "")
            if not playlist_id:
                return {"ok": False, "error": "no playlist_id provided"}
            track = self.spotify.add_current_track_to_playlist(playlist_id)
            if track is None:
                return {"ok": False, "error": "nothing is playing or the add failed"}
            return {"ok": True, **track}
        return {"ok": False, "error": f"unknown action: {action}"}

    async def start(self):
        server = await asyncio.start_server(
            self._handle_client, config.CONTROL_HOST, config.CONTROL_PORT
        )
        log.info(f"Control server listening on {config.CONTROL_HOST}:{config.CONTROL_PORT}")
        async with server:
            await server.serve_forever()
