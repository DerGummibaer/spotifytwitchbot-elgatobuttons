import streamDeck, {
  action,
  type KeyDownEvent,
  type WillAppearEvent,
  SingletonAction,
} from "@elgato/streamdeck";
import { sendCommand } from "../service-client";

type VolumeStepSettings = {
  step?: number;
};

const DEFAULT_STEP = 10;

@action({ UUID: "com.leon.spotifycontrol.volup" })
export class VolumeUpAction extends SingletonAction<VolumeStepSettings> {
  override async onWillAppear(ev: WillAppearEvent<VolumeStepSettings>): Promise<void> {
    const step = ev.payload.settings.step ?? DEFAULT_STEP;
    await ev.action.setTitle(`Vol\n+${step}`);
  }

  override async onKeyDown(ev: KeyDownEvent<VolumeStepSettings>): Promise<void> {
    const step = ev.payload.settings.step ?? DEFAULT_STEP;
    try {
      const result = await sendCommand({ action: "vol_adjust", delta: step });
      if (!result.ok) {
        await ev.action.showAlert();
      }
    } catch (err) {
      streamDeck.logger.error("vol_up failed", err);
      await ev.action.showAlert();
    }
  }
}
