import asyncio
import time
from collections import defaultdict

Event = dict
BUFFER_TTL_S = 600
BUFFER_MAX = 1000


class EventBus:
    """Per-search fan-out with a replay buffer so an SSE client that connects a moment after
    POST /searches still sees every event (spec §5.8)."""

    def __init__(self) -> None:
        self._subs: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._buffer: dict[str, list[Event]] = defaultdict(list)
        self._closed: dict[str, float] = {}

    def publish(self, search_id: str, type: str, data: dict) -> None:
        ev: Event = {"type": type, "data": data}
        buf = self._buffer[search_id]
        if len(buf) < BUFFER_MAX:
            buf.append(ev)
        for q in self._subs.get(search_id, []):
            q.put_nowait(ev)

    def subscribe(self, search_id: str) -> asyncio.Queue:
        self._gc()
        q: asyncio.Queue = asyncio.Queue()
        for ev in self._buffer.get(search_id, []):
            q.put_nowait(ev)
        if search_id in self._closed:
            q.put_nowait(None)
        else:
            self._subs[search_id].append(q)
        return q

    def close(self, search_id: str) -> None:
        for q in self._subs.pop(search_id, []):
            q.put_nowait(None)
        self._closed[search_id] = time.monotonic()

    def _gc(self) -> None:
        cutoff = time.monotonic() - BUFFER_TTL_S
        for sid in [s for s, t in self._closed.items() if t < cutoff]:
            self._closed.pop(sid, None)
            self._buffer.pop(sid, None)


bus = EventBus()
