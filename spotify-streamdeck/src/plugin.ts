import streamDeck from "@elgato/streamdeck";

import { SkipAction } from "./actions/skip";
import { PreviousAction } from "./actions/previous";
import { VolumeUpAction } from "./actions/volume-up";
import { VolumeDownAction } from "./actions/volume-down";
import { PlayPauseAction } from "./actions/play-pause";

if (!streamDeck || typeof streamDeck.logger?.setLevel !== "function") {
  // If this fires, it means the @elgato/streamdeck import didn't resolve
  // to the expected module shape -- almost always a bundler/interop issue,
  // not a problem with your Stream Deck setup. Re-run "npm run build"
  // after a clean "rm -rf node_modules && npm install" if you see this.
  console.error(
    "Fatal: streamDeck import did not resolve correctly. Got:",
    streamDeck
  );
  throw new Error("streamDeck SDK failed to load -- see console output above.");
}

streamDeck.logger.setLevel("info");

streamDeck.actions.registerAction(new SkipAction());
streamDeck.actions.registerAction(new PreviousAction());
streamDeck.actions.registerAction(new VolumeUpAction());
streamDeck.actions.registerAction(new VolumeDownAction());
streamDeck.actions.registerAction(new PlayPauseAction());

streamDeck.connect();
