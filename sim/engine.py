"""Simulation engine: clock + environment + ADC + firmware backend + output sinks."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field

import pandas as pd

from .adc import to_raw
from .blynk_mock import BlynkMock
from .config import Scenario
from .firmware_model import LED_PINS, FirmwareModel, HttpResponse, classify
from .physics import Environment


@dataclass
class TickRecord:
    t_ms: int
    wall: float
    truth: dict
    raws: dict[int, int]
    blynk: list
    leds: dict[int, int]
    serial: list[str]


@dataclass
class Clock:
    """``manual``: time moves only via Engine.step/advance_to (accelerated/batch).
    ``realtime``: sim time = wall time since start x speed."""

    mode: str = "manual"
    speed: float = 1.0
    _m0: float = field(default_factory=time.monotonic)

    def now_ms(self, manual_ms: int) -> int:
        if self.mode == "realtime":
            return int((time.monotonic() - self._m0) * 1000 * self.speed)
        return manual_ms

    def wall_of(self, t_ms: int) -> float:
        """Monotonic wall time at which sim time t_ms is due (realtime mode)."""
        return self._m0 + t_ms / 1000.0 / self.speed


def make_backend(kind: str):
    if kind == "python":
        return FirmwareModel()
    if kind == "fil":
        from .fil import FilFirmware

        return FilFirmware()
    raise ValueError(f"unknown backend {kind!r}")


class Engine:
    def __init__(self, scenario: Scenario, backend: str = "python", clock: Clock | None = None):
        self.sc = scenario
        self.env = Environment(scenario)
        self.backend_kind = backend
        self.fw = make_backend(backend)
        self.clock = clock or Clock()
        self.blynk = BlynkMock(token=scenario.blynk_token)
        self.leds: dict[int, int] = {p: 0 for p in LED_PINS}
        self.serial: deque[str] = deque(maxlen=500)
        self.history: deque[TickRecord] = deque(maxlen=5000)
        self.jitter_ms: deque[float] = deque(maxlen=100_000)
        self.lock = threading.RLock()
        self.tick_ms = round(scenario.tick_s * 1000)
        self._manual_ms = 0
        self._next_tick = self.tick_ms
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        ev = self.fw.setup()
        self._absorb(ev)

    # ---- time ----
    def now_ms(self) -> int:
        return self.clock.now_ms(self._manual_ms)

    def advance_to(self, t_ms: int) -> None:
        with self.lock:
            while self._next_tick <= t_ms:
                self._fire(self._next_tick)
                self._next_tick += self.tick_ms
            self._manual_ms = max(self._manual_ms, t_ms)

    def step(self, n: int = 1) -> None:
        """Accelerated mode: run n firmware ticks immediately."""
        self.advance_to(self._next_tick + (n - 1) * self.tick_ms)

    # ---- world ----
    def truth(self, t_ms: int) -> dict:
        return self.env.rig_truth(t_ms / 1000.0)

    def raws(self, t_ms: int) -> dict[int, int]:
        return to_raw(self.sc, self.truth(t_ms), t_ms)

    def _absorb(self, ev) -> None:
        self.leds.update(ev.leds)
        self.serial.extend(ev.serial)

    def _fire(self, t_ms: int) -> None:
        truth = self.truth(t_ms)
        raws = to_raw(self.sc, truth, t_ms)
        ev = self.fw.tick(t_ms, raws)
        wall = time.time()
        if self.clock.mode == "realtime":
            self.jitter_ms.append((time.monotonic() - self.clock.wall_of(t_ms)) * 1000)
        for pin, val in ev.blynk:
            self.blynk.write(pin, val, t_ms, wall)
        self._absorb(ev)
        self.history.append(
            TickRecord(t_ms, wall, truth, raws, ev.blynk, dict(self.leds), ev.serial)
        )

    # ---- HTTP surface of the firmware ----
    def api(self, t_ms: int | None = None) -> HttpResponse:
        with self.lock:
            t = self.now_ms() if t_ms is None else t_ms
            self.advance_to(t)
            return self.fw.api(t, self.raws(t))

    def api_v2(self, t_ms: int | None = None) -> dict:
        """N-panel farm view (emulator-only, versioned contract)."""
        with self.lock:
            t = self.now_ms() if t_ms is None else t_ms
            self.advance_to(t)
            t_s = t / 1000.0
            g = self.env.irradiance(t_s)
            panels = []
            for i in range(1, self.sc.farm.n_panels + 1):
                p = self.env.panel(f"P{i}", t_s)
                current = p.isc if p.voltage > 0 else 0.0
                panels.append(
                    {
                        "id": f"P{i}",
                        "voltage": round(p.voltage, 2),
                        "current": round(current, 2),
                        "power_w": round(0.75 * p.voltage * current, 2),
                        "status": classify(p.voltage).split(":")[0],
                    }
                )
            return {
                "schema": "solar-twin/v2",
                "t_ms": t,
                "timestamp": (self.env.times[0] + pd.Timedelta(milliseconds=t)).isoformat(),
                "irradiance_wm2": round(g, 1),
                "ambient_c": round(self.env.ambient(t_s), 2),
                "panels": panels,
            }

    # ---- realtime runner ----
    def start(self, poll_s: float = 0.01) -> None:
        if self.clock.mode != "realtime" or self._thread:
            return

        def run() -> None:
            while not self._stop.is_set():
                self.advance_to(self.now_ms())
                self._stop.wait(poll_s)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        close = getattr(self.fw, "close", None)
        if close:
            close()
