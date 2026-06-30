"""
Run this file to start the Twitch chat bot. It connects to the always-on
Spotify service (a separate program) over a local socket for every
Spotify-related command -- it does not run Spotify integration itself.

If the Spotify service isn't running, the bot still starts and chats
normally, but Spotify commands will reply that the service is offline
rather than crashing.
"""
import asyncio
import logging
import os
import sys

import config
from twitch_bot import MusicBot

os.makedirs(config.LOG_DIR, exist_ok=True)

# When packaged with PyInstaller's --windowed flag, there is no console
# and sys.stdout/stderr are None. Logging to a None stream raises
# AttributeError and crashes the app before it starts, so only attach
# the console handler when a real stream exists.
handlers = [logging.FileHandler(os.path.join(config.LOG_DIR, config.LOG_FILE))]
if sys.stdout is not None:
    handlers.append(logging.StreamHandler())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=handlers,
)

log = logging.getLogger("main")


async def main():
    bot = MusicBot()
    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down.")
