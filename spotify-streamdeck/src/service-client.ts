import { createConnection } from "node:net";

// This connects to the always-on Spotify service, not to the Twitch bot.
// The Twitch bot is a separate, optional program that talks to this same
// service -- this plugin has no dependency on it at all.
const HOST = "127.0.0.1";
const PORT = 9876;

export type NowPlaying = {
  ok: boolean;
  is_playing?: boolean;
  track?: string | null;
  artist?: string | null;
  album_art_url?: string | null;
};

export type Playlist = {
  id: string;
  name: string;
};

export type ControlResponse = {
  ok: boolean;
  volume?: number;
  error?: string;
  playlists?: Playlist[];
  name?: string;
  artist?: string;
} & NowPlaying;

/**
 * Sends one JSON command to the Spotify service's control socket and
 * waits for the single-line JSON reply. Opens a fresh connection each
 * call -- these are infrequent, human-triggered button presses, so the
 * overhead is irrelevant and a fresh connection avoids any stale-socket bugs.
 */
export function sendCommand(payload: Record<string, unknown>): Promise<ControlResponse> {
  return new Promise((resolve, reject) => {
    const socket = createConnection({ host: HOST, port: PORT });
    let buffer = "";

    const timeout = setTimeout(() => {
      socket.destroy();
      reject(new Error("control socket timed out -- is the Spotify service running?"));
    }, 3000);

    socket.on("connect", () => {
      socket.write(JSON.stringify(payload) + "\n");
    });

    socket.on("data", (chunk: Buffer) => {
      buffer += chunk.toString();
      if (buffer.includes("\n")) {
        clearTimeout(timeout);
        socket.end();
        try {
          resolve(JSON.parse(buffer.trim()));
        } catch {
          reject(new Error("invalid response from Spotify service"));
        }
      }
    });

    socket.on("error", (err: Error) => {
      clearTimeout(timeout);
      reject(err);
    });
  });
}
