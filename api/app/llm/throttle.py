import asyncio
import time
from collections import deque

WINDOW = 60.0


class TokenBucket:
    """Sliding 60 s window over requests and estimated tokens (spec §7.3)."""

    def __init__(self, rpm: int, tpm: int, clock=time.monotonic, sleep=asyncio.sleep):
        self.rpm, self.tpm, self.clock, self.sleep = rpm, tpm, clock, sleep
        self._events: deque[tuple[float, int]] = deque()

    def _trim(self) -> None:
        cutoff = self.clock() - WINDOW
        while self._events and self._events[0][0] <= cutoff:
            self._events.popleft()

    def _would_exceed(self, tokens: int) -> bool:
        return len(self._events) >= self.rpm or sum(t for _, t in self._events) + tokens > self.tpm

    async def acquire(self, tokens: int) -> None:
        self._trim()
        while self._events and self._would_exceed(tokens):
            wait = max(0.05, self._events[0][0] + WINDOW - self.clock())
            await self.sleep(wait)
            self._trim()
        self._events.append((self.clock(), tokens))
