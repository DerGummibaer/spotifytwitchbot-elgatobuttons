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
Copy the *contents* of the resulting `dist\SpotifyService\` folder into
`payload\SpotifyService\` here (not the folder itself nested inside
another folder -- the .exe should be directly inside `payload\SpotifyService\`).

Do NOT copy a `.env` or `.spotify_cache` file into this folder -- the
installer generates `.env` itself from what the user enters in the
wizard, and `.spotify_cache` gets created fresh on each user's machine
during their own one-time Spotify login.

**TwitchMusicBot folder** -- from the `twitch-music-bot` project, same idea:
```
pip install -r requirements.txt
pyinstaller --name TwitchMusicBot --windowed --onedir main.py
```
Copy the contents of `dist\TwitchMusicBot\` into `payload\TwitchMusicBot\`.

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
