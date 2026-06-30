import streamDeck, {
  action,
  type KeyDownEvent,
  type SendToPluginEvent,
  SingletonAction,
} from "@elgato/streamdeck";
import { sendCommand } from "../service-client";

type Settings = {
  playlistId?: string;
};

// sdpi-components data-source request payload shape -- see
// https://sdpi-components.dev/docs/helpers/data-source
type DataSourcePayload = {
  event: string;
};

@action({ UUID: "com.leon.spotifycontrol.addtoplaylist" })
export class AddToPlaylistAction extends SingletonAction<Settings> {
  override async onKeyDown(ev: KeyDownEvent<Settings>): Promise<void> {
    const playlistId = ev.payload.settings.playlistId;
    if (!playlistId) {
      streamDeck.logger.warn("add-to-playlist pressed with no playlist configured");
      await ev.action.showAlert();
      return;
    }

    try {
      const result = await sendCommand({ action: "add_to_playlist", playlist_id: playlistId });
      if (result.ok) {
        await ev.action.showOk();
      } else if (result.error === "launching_spotify") {
        await ev.action.showOk();
        await ev.action.setTitle("Starting\nSpotify...");
        setTimeout(() => ev.action.setTitle(""), 4000);
      } else {
        await ev.action.showAlert();
      }
    } catch (err) {
      streamDeck.logger.error("add-to-playlist failed", err);
      await ev.action.showAlert();
    }
  }

  /**
   * Handles the property inspector's request for the playlist dropdown's
   * options. Fetches the user's playlists from the Spotify service and
   * sends them back in the format sdpi-components expects.
   */
  override async onSendToPlugin(ev: SendToPluginEvent<DataSourcePayload, Settings>): Promise<void> {
    const payload = ev.payload;
    if (!payload || payload.event !== "getPlaylists") {
      return;
    }

    try {
      const result = await sendCommand({ action: "get_playlists" });
      const items = (result.playlists ?? []).map((p) => ({
        label: p.name,
        value: p.id,
      }));
      await streamDeck.ui.current?.sendToPropertyInspector({
        event: "getPlaylists",
        items,
      });
    } catch (err) {
      streamDeck.logger.error("failed to fetch playlists", err);
      await streamDeck.ui.current?.sendToPropertyInspector({
        event: "getPlaylists",
        items: [],
      });
    }
  }
}
