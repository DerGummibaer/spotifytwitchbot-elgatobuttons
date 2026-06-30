"""
Spotify's queue API has no idea who added a song. We maintain our own
ordered record of (requester -> track) so that !remove can find and
remove "the last thing this specific person requested".

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

    def recent(self, limit: int = 5) -> list[QueuedRequest]:
        pending = [r for r in self._requests if not r.removed]
        return pending[-limit:]
