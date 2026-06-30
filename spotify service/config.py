"""
Settings for the always-on Spotify service. This process owns the only
Spotify connection -- Stream Deck and the (optional) Twitch bot both talk
to it as clients over the local control socket, never to Spotify directly.
"""
import os
import sys
from dotenv import load_dotenv

# Resolve paths relative to the actual exe location (or this file, when run
# as a plain script), not the unreliable current working directory --
# important once this is packaged and launched at Windows startup, where
# the working directory is not guaranteed to be this folder.
if getattr(sys, "frozen", False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(base_dir, ".env"))

# --- Spotify ---
SPOTIFY_CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
SPOTIFY_SCOPES = "user-modify-playback-state user-read-playback-state user-read-currently-playing"
SPOTIFY_TOKEN_CACHE = os.path.join(base_dir, ".spotify_cache")

# --- Local control socket ---
# Stream Deck and the Twitch bot both connect here. Keep this value in
# sync with CONTROL_PORT in the Twitch bot's own .env, and with the port
# hardcoded in the Stream Deck plugin's src/bot-client.ts, if you ever
# change it from the default.
CONTROL_HOST = os.environ.get("CONTROL_HOST", "127.0.0.1")
CONTROL_PORT = int(os.environ.get("CONTROL_PORT", "9876"))

VOLUME_STEP = 10  # default step for vol_up/vol_down when no delta is given

# --- Logging ---
LOG_DIR = os.path.join(base_dir, "logs")
LOG_FILE = "spotify_service.log"
