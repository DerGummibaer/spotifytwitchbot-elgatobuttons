"""
All tunable settings live here. Change permission levels or cooldowns
by editing the values below -- no need to touch any other file.

This bot no longer talks to Spotify directly. It's a client of the
always-on Spotify service (see the separate spotify-service project),
exactly like the Stream Deck plugin is. The bot can be started, stopped,
or left off entirely without affecting Spotify playback or the
Stream Deck buttons.
"""
import os
import sys
from dotenv import load_dotenv

# When run as a plain script, .env sits next to this file. When packaged
# with PyInstaller, sys.executable points at the .exe itself, and the
# current working directory can't be relied on. Resolving explicitly
# avoids "works with python main.py, breaks as a packaged exe" bugs.
if getattr(sys, "frozen", False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(base_dir, ".env"))

# --- Credentials (from .env, never hardcode these) ---
TWITCH_OAUTH_TOKEN = os.environ["TWITCH_OAUTH_TOKEN"]
TWITCH_BOT_USERNAME = os.environ["TWITCH_BOT_USERNAME"]
TWITCH_CHANNEL = os.environ["TWITCH_CHANNEL"].lower()
TWITCH_BROADCASTER_USERNAME = os.environ["TWITCH_BROADCASTER_USERNAME"].lower()

# --- Spotify service connection ---
# This must match CONTROL_HOST / CONTROL_PORT in the spotify-service
# project's own .env -- they're two different programs, but they need
# to agree on where the service is listening.
SERVICE_HOST = os.environ.get("SERVICE_HOST", "127.0.0.1")
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "9876"))

# --- Permission levels ---
# Each command maps to a minimum required level.
# Levels, from lowest to highest: "everyone", "subscriber", "moderator", "broadcaster"
# A user must be AT OR ABOVE the listed level to use the command.
PERMISSIONS = {
    "sr": "subscriber",      # !sr -- subs, mods, broadcaster
    "remove": "subscriber",  # !remove -- subs, mods, broadcaster
    "vol": "everyone",       # !vol -- anyone
    "skip": "everyone",      # !skip -- anyone (flagged as open; change to "subscriber" later if needed)
    "sq": "everyone",        # !sq -- anyone
}

# Order matters: index = rank. Higher index = more privilege.
LEVEL_RANK = ["everyone", "subscriber", "moderator", "broadcaster"]

# --- Cooldowns (seconds). 0 = no cooldown. ---
COOLDOWNS = {
    "sr": 5,
    "remove": 5,
    "vol": 3,
    "skip": 10,
    "sq": 10,
}

# --- Song request behavior ---
MAX_QUEUE_PER_USER = 2  # how many pending requests one user can have at once

# --- Logging ---
LOG_DIR = os.path.join(base_dir, "logs")
LOG_FILE = "bot.log"
