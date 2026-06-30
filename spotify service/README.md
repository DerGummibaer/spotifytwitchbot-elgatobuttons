# Spotify service

The always-on background service that owns the actual Spotify connection.
Stream Deck and the (optional) Twitch bot both connect to this over a
local socket -- neither talks to Spotify directly. This is the only
piece that needs to be running for the Stream Deck buttons to work.

## One-time setup

1. **Install dependencies**

   ```
   pip install -r requirements.txt
   ```

2. **Create your `.env` file**

   Copy `.env.example` to `.env` and fill in:
   - `SPOTIFY_CLIENT_ID` — from https://developer.spotify.com/dashboard
     (create an app, add `http://127.0.0.1:8888/callback` as a redirect URI).

   **Never share this file or paste its contents anywhere.**

3. **Link Spotify (one time, opens a browser)**

   ```
   python spotify_client.py
   ```

   Log in and approve. This creates a local `.spotify_cache` file so the
   service won't ask again -- it refreshes silently from then on.

## Running it directly (for testing)

```
python main.py
```

Leave this running and test with the Stream Deck buttons, or with:

```json
{"action": "now_playing"}
```

sent to `127.0.0.1:9876` from any tool that can open a raw TCP socket.

## Building the .exe

```
pyinstaller --name SpotifyService --windowed --onedir main.py
```

This produces `dist/SpotifyService/SpotifyService.exe`. Copy your `.env`
(and `.spotify_cache`, if you've already done the one-time login) into
that same `dist/SpotifyService/` folder -- the exe looks for them right
next to itself.

Test it by double-clicking `SpotifyService.exe` directly first, then
checking `dist/SpotifyService/logs/spotify_service.log` for a
"Spotify connected" line.

## Making it start automatically with Windows

This should start on its own, independent of OBS or anything else,
since both Stream Deck and the Twitch bot depend on it being available
at any time.

**Recommended: Task Scheduler** (more reliable than the Startup folder
for a background service -- it can restart automatically on failure,
and doesn't depend on the visible desktop finishing loading first):

1. Open **Task Scheduler** (search for it in the Start menu).
2. **Create Task...** (not "Create Basic Task" -- the full dialog gives
   more control).
3. **General tab**: name it "Spotify Service". Check
   "Run whether user is logged on or not" if you want it available even
   before you sign in, or leave the default if that's not needed.
4. **Triggers tab** → **New...** → "At log on" (for the current user).
5. **Actions tab** → **New...** → **Start a program** → browse to
   `dist/SpotifyService/SpotifyService.exe`.
6. **Conditions tab**: uncheck "Start the task only if the computer is
   on AC power" if this is a laptop, so it still runs on battery.
7. Save. Log off and back on (or just reboot) to confirm it starts
   automatically -- check `logs/spotify_service.log` for a fresh
   "Spotify connected" line after logging back in.

**Simpler alternative: Startup folder.** Press `Win+R`, type
`shell:startup`, and drop a shortcut to `SpotifyService.exe` in the
folder that opens. Less robust than Task Scheduler (no auto-restart on
crash, and it only runs after a full desktop login), but quicker to set
up if that's good enough for your use.

## Stopping it

Since this runs invisibly (no console, no taskbar icon), close it via
**Task Manager → Details tab → SpotifyService.exe → End task**, the
same way you'd close the Twitch bot's exe.

## Control socket reference

Listens on `127.0.0.1:9876` by default (configurable via `CONTROL_PORT`
in `.env`). One JSON command per line, one JSON response back:

```json
{"action": "vol_up"}
{"action": "vol_down"}
{"action": "vol_adjust", "delta": -15}
{"action": "vol_set", "value": 50}
{"action": "get_volume"}
{"action": "skip"}
{"action": "previous"}
{"action": "play_pause"}
{"action": "now_playing"}
{"action": "queue_add", "query": "spotify:track:... or a song name"}
{"action": "get_queue", "limit": 5}
```

Both the Stream Deck plugin and the Twitch bot use this same set of
commands -- they're peers, not in a parent/child relationship. Either
one can be running, both, or neither (in which case nothing controls
Spotify, but nothing crashes either).
