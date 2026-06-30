import streamDeck, { action, type KeyDownEvent, SingletonAction } from "@elgato/streamdeck";
import { sendCommand } from "../service-client";

@action({ UUID: "com.leon.spotifycontrol.skip" })
export class SkipAction extends SingletonAction {
  override async onKeyDown(ev: KeyDownEvent): Promise<void> {
    try {
      const result = await sendCommand({ action: "skip" });
      if (!result.ok) {
        await ev.action.showAlert();
      }
    } catch (err) {
      streamDeck.logger.error("skip failed", err);
      await ev.action.showAlert();
    }
  }
}
