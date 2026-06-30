import streamDeck, {
  action,
  type KeyDownEvent,
  type WillAppearEvent,
  type WillDisappearEvent,
  type ActionInstance,
  SingletonAction,
} from "@elgato/streamdeck";
import { sendCommand } from "../service-client";
import { fetchImageAsDataUri } from "../image-cache";

const POLL_INTERVAL_MS = 5000;

@action({ UUID: "com.leon.spotifycontrol.playpause" })
export class PlayPauseAction extends SingletonAction {
  // one poll timer per visible key instance, keyed by action context
  private pollTimers = new Map<string, ReturnType<typeof setInterval>>();
  // tracks the last album art URL shown per key, so we skip re-downloading
  // the same image every 5 seconds when the song hasn't changed
  private lastArtUrl = new Map<string, string | null>();

  override async onWillAppear(ev: WillAppearEvent): Promise<void> {
    await this.refreshImage(ev.action);
    const timer = setInterval(() => this.refreshImage(ev.action), POLL_INTERVAL_MS);
    this.pollTimers.set(ev.action.id, timer);
  }

  override onWillDisappear(ev: WillDisappearEvent): void {
    const timer = this.pollTimers.get(ev.action.id);
    if (timer) {
      clearInterval(timer);
      this.pollTimers.delete(ev.action.id);
    }
    this.lastArtUrl.delete(ev.action.id);
  }

  override async onKeyDown(ev: KeyDownEvent): Promise<void> {
    try {
      const result = await sendCommand({ action: "play_pause" });
      if (!result.ok) {
        await ev.action.showAlert();
        return;
      }
      // refresh immediately rather than waiting for the next poll tick,
      // so the button feels responsive right after a press
      await this.refreshImage(ev.action);
    } catch (err) {
      streamDeck.logger.error("play_pause failed", err);
      await ev.action.showAlert();
    }
  }

  private async refreshImage(actionInstance: ActionInstance): Promise<void> {
    try {
      const state = await sendCommand({ action: "now_playing" });

      if (!state.ok || !state.track || !state.album_art_url) {
        // nothing playing, or no art available -- fall back to the
        // manifest's default key image rather than showing a blank key
        this.lastArtUrl.set(actionInstance.id, null);
        await actionInstance.setTitle("");
        await actionInstance.setImage();
        return;
      }

      // skip re-downloading if the song (and therefore the art) hasn't changed
      if (this.lastArtUrl.get(actionInstance.id) === state.album_art_url) {
        return;
      }

      const dataUri = await fetchImageAsDataUri(state.album_art_url);
      await actionInstance.setTitle("");
      await actionInstance.setImage(dataUri);
      this.lastArtUrl.set(actionInstance.id, state.album_art_url);
    } catch (err) {
      streamDeck.logger.error("now_playing poll failed", err);
      // leave whatever image was last shown rather than clearing it on a
      // transient network blip; only show "offline" via title if we have
      // no art at all yet for this key
      if (!this.lastArtUrl.get(actionInstance.id)) {
        await actionInstance.setTitle("Service\noffline");
      }
    }
  }
}
