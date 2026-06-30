// Downloads an image from a URL and returns it as a base64 data URI that
// Stream Deck's setImage() accepts. Caches a handful of recent results so
// re-polling the same song's art doesn't re-download it every 5 seconds.

const cache = new Map<string, string>();
const MAX_CACHE_ENTRIES = 20;

export async function fetchImageAsDataUri(url: string): Promise<string> {
  const cached = cache.get(url);
  if (cached) return cached;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`failed to fetch image: ${response.status} ${response.statusText}`);
  }

  const contentType = response.headers.get("content-type") ?? "image/jpeg";
  const buffer = Buffer.from(await response.arrayBuffer());
  const dataUri = `data:${contentType};base64,${buffer.toString("base64")}`;

  if (cache.size >= MAX_CACHE_ENTRIES) {
    const oldestKey = cache.keys().next().value;
    if (oldestKey !== undefined) cache.delete(oldestKey);
  }
  cache.set(url, dataUri);

  return dataUri;
}
