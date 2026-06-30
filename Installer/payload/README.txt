# Payload folder

The installer script (`SpotifyStreamDeckSuite.iss`) expects this folder to
contain the pre-built artifacts below before you compile. Inno Setup
doesn't build your code -- it only packages files that already exist.

## Required layout

```
payload\
  SpotifyService\              <- the ENTIRE dist\SpotifyService\ folder contents
    SpotifyService.exe
    _internal\
    ... (everything PyInstaller produced)
  TwitchMusicBot\               <- the ENTIRE dist\TwitchMusicBot\ folder contents
    TwitchMusicBot.exe
    _internal\
    ...
  com.leon.spotifycontrol.streamDeckPlugin   <- the single packaged plugin file
```

## How to produce each piece

**SpotifyService folder** -- from the `spotify-service` project:
```
pip install -r requirements.txt
pyinstaller --name SpotifyService --windowed --onedir main.py
```

⚠️ IMPORTANT -- after PyInstaller runs, open `dist\SpotifyService\` in File
Explorer. You should see `SpotifyService.exe` and `_internal\` sitting
directly inside it. Select BOTH of those items (Ctrl+A), copy them, then
paste into `payload\SpotifyService\` here.

Do NOT copy the `dist` folder itself, or the `dist\SpotifyService` folder
itself -- only copy the CONTENTS. The end result must be:

    payload\SpotifyService\SpotifyService.exe       <- directly here
    payload\SpotifyService\_internal\               <- directly here

NOT:

    payload\SpotifyService\dist\SpotifyService\SpotifyService.exe  <- WRONG

Do NOT copy a `.env` or `.spotify_cache` file into this folder -- the
installer generates `.env` itself from what the user enters in the
wizard, and `.spotify_cache` gets created fresh on each user's machine
during their own one-time Spotify login.

**TwitchMusicBot folder** -- from the `twitch-music-bot` project, same idea:
```
pip install -r requirements.txt
pyinstaller --name TwitchMusicBot --windowed --onedir main.py
```

⚠️ Same rule applies: copy only the CONTENTS of `dist\TwitchMusicBot\`
into `payload\TwitchMusicBot\`. The result must be:

    payload\TwitchMusicBot\TwitchMusicBot.exe       <- directly here
    payload\TwitchMusicBot\_internal\               <- directly here

**The .streamDeckPlugin file** -- from the `spotify-streamdeck` project:
```
npm install
npm run build
streamdeck pack com.leon.spotifycontrol.sdPlugin
```
This produces `com.leon.spotifycontrol.streamDeckPlugin` in that project's
folder. Copy that single file directly into `payload\` here (not into a
subfolder).

## Once the payload folder is ready

Open `SpotifyStreamDeckSuite.iss` in Inno Setup and click **Build → Compile**
(or press Ctrl+F9). The finished installer appears in `output\SpotifyStreamDeckSuiteSetup.exe`.

## Known gap worth testing yourself before sharing this

The installer launches `SpotifyService.exe` directly (via `Exec`) right
after install, to trigger the one-time Spotify browser login. The
Task Scheduler entry it also creates (`SpotifyStreamDeckService`, set to
run at next logon) is separate from that directly-launched instance --
the installer does not itself verify that the *scheduled* copy starts
correctly. Before sharing this installer with anyone else, test a full
log-off/log-on cycle yourself after installing, and confirm
`SpotifyService\logs\spotify_service.log` shows a fresh "Spotify
connected" line after logging back in -- that's the real proof the
autostart path works, not just the manual one triggered during install.
