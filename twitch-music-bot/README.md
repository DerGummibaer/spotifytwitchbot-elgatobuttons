# Twitch music bot

Optional Twitch chat commands (`!sr`, `!vol`, `!skip`, `!remove`, `!sq`)
for controlling Spotify. This bot does not talk to Spotify directly --
it's a client of the always-on **Spotify service** (a separate project),
exactly like the Stream Deck plugin is. You can run this bot, not run
it, start it late, or stop it early, and the Spotify service / Stream
Deck buttons are completely unaffected either way.

**This bot requires the Spotify service to be running** for its
commands to actually do anything -- see the `spotify-service` project's
own README for that setup, which should be done first.

## One-time setup

1. **Install dependencies**

   ```
   pip install -r requirements.txt
   ```

2. **Create your `.env` file**

   Copy `.env.example` to `.env` and fill in:

   - `TWITCH_OAUTH_TOKEN` — from https://twitchtokengenerator.com (Bot Chat Token).
     Paste it WITHOUT the `oauth:` prefix.
   - `TWITCH_BOT_USERNAME` — the account the bot logs in as.
   - `TWITCH_CHANNEL` — your channel name, lowercase.
   - `TWITCH_BROADCASTER_USERNAME` — your own username, for permission checks.
   - `SERVICE_HOST` / `SERVICE_PORT` — where the Spotify service is
     listening. Defaults (`127.0.0.1` / `9876`) match the service's own
     defaults, so you usually don't need to change these unless you
     changed them on the service side too.

   **Never share this file or paste its contents anywhere.**

## Running the bot

```
python main.py
```

If the Spotify service isn't running when a chat command is used, the
bot replies in chat that the service is offline, rather than crashing.

## Commands

| Command | Who can use it | What it does |
|---|---|---|
| `!sr <song or link>` | Subs, mods, you | Adds a song to the Spotify queue |
| `!vol <0-100>` | Everyone | Sets playback volume. No number = shows current volume |
| `!skip` | Everyone (changeable, see below) | Skips the current song |
| `!remove` | Subs, mods, you | Removes your own last pending request |
| `!sq` | Everyone | Lists the next few songs in queue |

## Changing who can use a command

Edit `config.py` → the `PERMISSIONS` dict. Levels are
`"everyone"`, `"subscriber"`, `"moderator"`, `"broadcaster"`. For example,
to restrict `!skip` to subs and above later:

```python
PERMISSIONS = {
    ...
    "skip": "subscriber",
}
```

No other file needs to change.

## Changing cooldowns

Also in `config.py`, the `COOLDOWNS` dict (seconds per command, per user).

## Building a real .exe

```
pyinstaller --name TwitchMusicBot --windowed --onedir main.py
```

Copy your `.env` into the resulting `dist/TwitchMusicBot/` folder, then
test by double-clicking `TwitchMusicBot.exe` and checking
`dist/TwitchMusicBot/logs/bot.log`.

## Running automatically with OBS (optional)

Since this bot is now independent of the Spotify service and the
Stream Deck buttons, whether and how you auto-start it is entirely up
to you -- it no longer needs to coordinate startup order with anything
else. If you still want it tied to your stream sessions specifically
(rather than always-on like the Spotify service), OBS Autostarter works
the same way as before:

1. Build the `.exe` (above) if you haven't already.
2. Install the OBS Autostarter plugin from
   https://obsproject.com/forum/resources/autostarter.2083/
3. Point it at `dist/TwitchMusicBot/TwitchMusicBot.exe`.

## Known limitation: !remove

Spotify's Web API has no endpoint to remove an arbitrary song from the
playback queue once it's been added — only "skip to next". `!remove`
works around this by no longer counting the song against the user's
request limit, and gives a heads up in chat. If the song has already
reached the front of the queue, it may still play. This matches a real
constraint of Spotify's API, not a bug in this bot.
