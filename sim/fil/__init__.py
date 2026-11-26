"""Firmware-in-the-loop: compile the *unmodified* Solar_Farm.ino for the host and drive it.

The sketch is compiled with a C++ shim of the Arduino/WiFi/WebServer/Blynk APIs
(``sim/fil/include``). The resulting process speaks a line protocol (see main.cpp); this
module wraps it in the same interface as :class:`sim.firmware_model.FirmwareModel`.
"""

from __future__ import annotations

import hashlib
import os
import queue
import shutil
import subprocess
import threading
from pathlib import Path

from ..adc import PIN_A, PIN_B, PIN_C, PIN_D
from ..firmware_model import Events, HttpResponse

HERE = Path(__file__).parent
REPO = HERE.parent.parent
DEFAULT_SKETCH = REPO / "Solar_Farm.ino"
BUILD_DIR = REPO / "build" / "fil"


class FilError(RuntimeError):
    pass


class FilTimeout(FilError):
    """The firmware did not answer in time (e.g. blocked in a busy-wait loop)."""


def compiler() -> str | None:
    return (
        os.environ.get("CXX")
        or shutil.which("c++")
        or shutil.which("g++")
        or shutil.which("clang++")
    )


def sketch_path() -> Path:
    return Path(os.environ.get("SOLAR_SKETCH", DEFAULT_SKETCH)).resolve()


def build(sketch: Path | None = None) -> Path:
    """Compile (cached by content hash) and return the path of the FIL executable."""
    sketch = (sketch or sketch_path()).resolve()
    cxx = compiler()
    if not cxx:
        raise FilError("no C++ compiler found (set CXX)")
    sources = [
        sketch,
        HERE / "shim.cpp",
        HERE / "main.cpp",
        *sorted((HERE / "include").glob("*.h")),
    ]
    h = hashlib.sha256()
    for s in sources:
        h.update(s.read_bytes())
    exe = BUILD_DIR / f"fil-{h.hexdigest()[:12]}"
    if exe.exists():
        return exe
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        cxx, "-std=c++17", "-O1", "-w",
        f"-I{HERE / 'include'}", "-include", "Arduino.h",
        "-x", "c++", str(sketch), "-x", "none",
        str(HERE / "shim.cpp"), str(HERE / "main.cpp"),
        "-o", str(exe),
    ]  # fmt: skip
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise FilError(f"FIL build failed:\n{res.stderr}")
    return exe


class FilProcess:
    """A running FIL firmware instance."""

    def __init__(self, exe: Path | None = None, timeout_s: float = 2.0):
        self.exe = exe or build()
        self.timeout_s = timeout_s
        self.proc = subprocess.Popen(
            [str(self.exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1
        )
        self._q: queue.Queue[str | None] = queue.Queue()
        threading.Thread(target=self._reader, daemon=True).start()
        self.dead = False

    def _reader(self) -> None:
        assert self.proc.stdout
        for line in self.proc.stdout:
            self._q.put(line.rstrip("\n"))
        self._q.put(None)

    def command(self, *lines: str) -> list[str]:
        """Send commands; return all event lines up to the last END."""
        if self.dead:
            raise FilError("FIL process is not responsive")
        assert self.proc.stdin
        self.proc.stdin.write("".join(f"{ln}\n" for ln in lines))
        self.proc.stdin.flush()
        out: list[str] = []
        ends = 0
        while ends < len(lines):
            try:
                item = self._q.get(timeout=self.timeout_s)
            except queue.Empty:
                self.dead = True
                self.close()
                raise FilTimeout(f"no response to {lines[-1]!r} within {self.timeout_s}s") from None
            if item is None:
                self.dead = True
                raise FilError("FIL process exited")
            if item == "END":
                ends += 1
            else:
                out.append(item)
        return out

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait(timeout=5)


def parse_events(lines: list[str]) -> tuple[Events, list[HttpResponse]]:
    ev, http = Events(), []
    for ln in lines:
        kind, *rest = ln.split("\t")
        if kind == "LED":
            ev.leds[int(rest[0])] = int(rest[1])
        elif kind == "BLYNK":
            pin, val = int(rest[0]), rest[1]
            try:
                ev.blynk.append((pin, float(val)))
            except ValueError:
                ev.blynk.append((pin, val))
        elif kind == "SERIAL":
            ev.serial.append(rest[0] if rest else "")
        elif kind == "HTTP":
            code, ctype, hdrs, body = int(rest[0]), rest[1], rest[2], rest[3]
            headers = {}
            for h in filter(None, hdrs.split("\x1f")):
                k, _, v = h.partition(": ")
                headers[k] = v
            http.append(HttpResponse(code, ctype, body, headers))
        elif kind == "ERROR":
            raise FilError(ln)
    return ev, http


class FilFirmware:
    """Backend with the same interface as FirmwareModel, executing the real sketch."""

    name = "fil"

    def __init__(self, exe: Path | None = None, wifi: bool = True, timeout_s: float = 2.0):
        self.p = FilProcess(exe, timeout_s=timeout_s)
        self.wifi = wifi

    def _adc(self, raws: dict[int, int]) -> list[str]:
        return [f"ADC {pin} {raws[pin]}" for pin in (PIN_A, PIN_B, PIN_C, PIN_D)]

    def setup(self) -> Events:
        ev, _ = parse_events(self.p.command(f"WIFI {int(self.wifi)}", "TIME 0", "SETUP"))
        return ev

    def tick(self, t_ms: int, raws: dict[int, int]) -> Events:
        ev, _ = parse_events(self.p.command(*self._adc(raws), f"TIME {t_ms}", "LOOP"))
        return ev

    def api(self, t_ms: int, raws: dict[int, int], uri: str = "/api") -> HttpResponse:
        _, http = parse_events(self.p.command(*self._adc(raws), f"TIME {t_ms}", f"GET {uri}"))
        if not http:
            raise FilError("firmware produced no HTTP response")
        return http[-1]

    def close(self) -> None:
        self.p.close()
