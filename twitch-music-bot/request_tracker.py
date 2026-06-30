"""
Spotify's queue API has no idea who added a song. We maintain our own
ordered record of (requester -> track) so that !remove can find and
remove "the last thing this specific person requested".

Removed tracks are added to a skip_list so the auto-skip poll in
twitch_bot.py can detect them coming up as now-playing and skip them
automatically -- working around Spotify's lack of a remove-from-queue API.

This is in-memory only and resets when the bot restarts -- that's fine,
since it only needs to track requests made during the current session.
"""
from dataclasses import dataclass, field
import time


@dataclass
class QueuedRequest:
    requester: str
    track_uri: str
    track_name: str
    track_artist: str
    requested_at: float = field(default_factory=time.time)
    removed: bool = False


class RequestTracker:
    def __init__(self):
        self._requests: list[QueuedRequest] = []
        self._skip_uris: set[str] = set()

    def add(self, requester: str, track_uri: str, track_name: str, track_artist: str) -> None:
        self._requests.append(
            QueuedRequest(
                requester=requester.lower(),
                track_uri=track_uri,
                track_name=track_name,
                track_artist=track_artist,
            )
        )

    def count_pending_for(self, requester: str) -> int:
        requester = requester.lower()
        return sum(1 for r in self._requests if r.requester == requester and not r.removed)

    def last_pending_for(self, requester: str) -> QueuedRequest | None:
        requester = requester.lower()
        for r in reversed(self._requests):
            if r.requester == requester and not r.removed:
                return r
        return None

    def mark_removed(self, request: QueuedRequest) -> None:
        request.removed = True
        self._skip_uris.add(request.track_uri)

    def should_skip(self, track_uri: str) -> bool:
        """Returns True if this track was !removed and should be auto-skipped."""
        return track_uri in self._skip_uris

    def clear_skip(self, track_uri: str) -> None:
        """Called after auto-skipping so we don't skip it again next poll."""
        self._skip_uris.discard(track_uri)

    def recent(self, limit: int = 5) -> list[QueuedRequest]:
        pending = [r for r in self._requests if not r.removed]
        return pending[-limit:]
