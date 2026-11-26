"""Mock Blynk Cloud: records firmware virtualWrite() calls and serves a Blynk-like HTTP API."""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class BlynkWrite:
    pin: int
    value: object
    t_ms: int  # simulated time of the write
    wall: float  # wall-clock time.time() of the write


class BlynkMock:
    def __init__(self, token: str = "sim-token", maxlen: int = 50_000):
        self.token = token
        self.writes: deque[BlynkWrite] = deque(maxlen=maxlen)
        self.latest: dict[int, object] = {}
        self._by_pin: dict[int, deque[BlynkWrite]] = defaultdict(lambda: deque(maxlen=maxlen))
        self._lock = threading.Lock()

    def write(self, pin: int, value: object, t_ms: int, wall: float) -> None:
        w = BlynkWrite(pin, value, t_ms, wall)
        with self._lock:
            self.writes.append(w)
            self._by_pin[pin].append(w)
            self.latest[pin] = value

    def history(self, pin: int) -> list[BlynkWrite]:
        with self._lock:
            return list(self._by_pin[pin])

    def datastreams(self) -> dict[str, object]:
        with self._lock:
            return {f"V{p}": v for p, v in sorted(self.latest.items())}
