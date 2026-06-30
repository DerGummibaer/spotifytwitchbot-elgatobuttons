# Spotify control - Stream Deck plugin

Five buttons that talk to the always-on **Spotify service** over its
local control socket. The service must be running for any of these to
work -- see the separate `spotify-service` project for that setup. This
plugin has no dependency on the Twitch bot at all; the two are
independent clients of the same service.

## Buttons

| Button | Behavior |
|---|---|
| Skip | Skips to the next song |
| Previous | Goes back to the previous song |
| Volume up | Raises volume by a configurable step (default 10) |
| Volume down | Lowers volume by a configurable step (default 10) |
| Play/pause | Toggles playback. Shows the current song's album art, refreshed every 5 seconds |

## Setting the volume step

Click a Volume up/down button in the Stream Deck app, then in the panel on
the right, type a number (1-50) into the **Step size** field. Each key
remembers its own step independently, so Volume up and Volume down can use
different amounts if you want.

## One-time setup

1. **Install dependencies**

   ```
   cd spotify-streamdeck
   npm install
   ```

2. **Link the plugin into Stream Deck**

   ```
   streamdeck link com.leon.spotifycontrol.sdPlugin
   ```

3. **Build and watch**

   ```
   npm run watch
   ```

   The five actions should now appear in Stream Deck's action list, under
   the "Spotify control" category. Drag them onto any keys you like.

4. **Make sure the Spotify service is running** before testing the
   buttons — without it, pressing a key will flash a red "!" (Stream
   Deck's built-in error indicator) and the Play/pause button's title
   will read "Service offline".

## Changing the control socket address or port

If you changed `CONTROL_HOST` / `CONTROL_PORT` in the Spotify service's
`.env` file away from the defaults (`127.0.0.1` / `9876`), update the
matching constants near the top of `src/service-client.ts`, then run
`npm run build` again.

## Finishing up: installing as a real plugin (no terminal needed)

`npm run watch` is a development workflow -- it rebuilds on every file
change, but it's not how a finished plugin should run day-to-day. Once
you're happy with the plugin, switch to running it as Stream Deck would
run any installed plugin:

1. Stop `npm run watch` (Ctrl+C) if it's still running.
2. Run a final production build:

   ```
   npm run build
   ```

3. Package it:

   ```
   streamdeck pack com.leon.spotifycontrol.sdPlugin
   ```

   This produces a `.streamDeckPlugin` file in the project folder.

4. Double-click that `.streamDeckPlugin` file. Stream Deck will install
   it like any other plugin -- no terminal, no `npm`, nothing left
   running in the background that you have to manage. Your existing
   button placements should carry over automatically since the action
   UUIDs haven't changed.

5. You can now safely delete or ignore the `node_modules` folder and
   anything related to `npm run watch` -- the installed plugin runs
   itself, exactly like any plugin from the Marketplace. Stream Deck
   restarts it automatically whenever the app itself restarts or your
   computer reboots.

If you ever want to make further code changes later, you'll go back to
the `npm run watch` workflow temporarily, then repeat this packaging
step when you're done. The same `.streamDeckPlugin` file this produces
is also what you'd share if you ever wanted to install this on another
computer.
