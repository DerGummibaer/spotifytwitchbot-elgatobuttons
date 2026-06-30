"""
Thin async client for the Spotify service's local control socket. The
Twitch bot uses this instead of talking to Spotify directly -- this
mirrors exactly what the Stream Deck plugin's bot-client.ts does, just
in Python. Opens a fresh connection per call; these are infrequent,
chat-triggered commands, so the overhead is irrelevant.
"""
import asyncio
import json

import config


class ServiceUnavailable(Exception):
    """Raised when the Spotify service can't be reached at all."""


async def send_command(payload: dict, timeout: float = 5.0) -> dict:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(config.SERVICE_HOST, config.SERVICE_PORT),
            timeout=timeout,
        )
    except (ConnectionRefusedError, OSError, asyncio.TimeoutError) as e:
        raise ServiceUnavailable(
            "Couldn't reach the Spotify service -- is it running?"
        ) from e

    try:
        writer.write((json.dumps(payload) + "\n").encode())
        await writer.drain()
        line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        if not line:
            raise ServiceUnavailable("Spotify service closed the connection with no response.")
        return json.loads(line.decode().strip())
    finally:
        writer.close()
        await writer.wait_closed()
