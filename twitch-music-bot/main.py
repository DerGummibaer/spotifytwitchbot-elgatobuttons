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
from credential_prompt import needs_credentials, prompt_for_credentials
from twitch_bot import MusicBot

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


async def main():
    bot = MusicBot()
    await bot.start()


if __name__ == "__main__":
    # Check for missing credentials before starting the asyncio loop --
    # tkinter must run synchronously on the main thread, and this is the
    # last safe point before asyncio.run() takes over.
    if needs_credentials():
        prompt_for_credentials()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down.")
