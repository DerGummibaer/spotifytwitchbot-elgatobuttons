import streamDeck, { action, type KeyDownEvent, SingletonAction } from "@elgato/streamdeck";
import { sendCommand } from "../service-client";

@action({ UUID: "com.leon.spotifycontrol.previous" })
export class PreviousAction extends SingletonAction {
  override async onKeyDown(ev: KeyDownEvent): Promise<void> {
    try {
      const result = await sendCommand({ action: "previous" });
      if (!result.ok) {
        if (result.error === "launching_spotify") {
          await ev.action.showOk();
          await ev.action.setTitle("Starting\nSpotify...");
          setTimeout(() => ev.action.setTitle(""), 4000);
          return;
        }
        await ev.action.showAlert();
      }
    } catch (err) {
      streamDeck.logger.error("previous failed", err);
      await ev.action.showAlert();
    }
  }
}
