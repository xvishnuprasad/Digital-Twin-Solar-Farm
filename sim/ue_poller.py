"""Reference client standing in for the Unreal Engine twin (VaRest / UE HTTP module).

Polls GET /api at a fixed interval, validates every payload against the v1 contract and
derives what the UE blueprint would render: per-panel material colour + HUD labels.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from .contracts import check_v1_body

COLOUR = {"RED": (1.0, 0.0, 0.0), "YELLOW": (1.0, 0.8, 0.0), "GREEN": (0.0, 1.0, 0.0)}


@dataclass
class TwinFrame:
    wall: float
    ok: bool
    errors: list[str] = field(default_factory=list)
    hud: dict[str, str] = field(default_factory=dict)
    material: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    body: str = ""


def frame_from_body(body: str, wall: float) -> TwinFrame:
    errs = check_v1_body(body)
    if errs:
        return TwinFrame(wall, False, errs, body=body)
    import json

    d = json.loads(body)
    hud = {
        "A": f"{d['PanelA_Voltage']:.2f} V",
        "B": f"{d['PanelB_Voltage']:.2f} V",
        "C": f"{d['PanelC_Voltage']:.2f} V",
        "D": f"{d['PanelD_Current']:.2f} A",
    }
    ab = COLOUR[d["Status_PanelAB"].split(":")[0]]
    c = COLOUR[d["Status_PanelC"].split(":")[0]]
    return TwinFrame(wall, True, [], hud, {"A": ab, "B": ab, "C": c, "D": c}, body)


def poll(
    url: str, interval_s: float = 2.0, count: int = 5, timeout_s: float = 2.0
) -> list[TwinFrame]:
    frames: list[TwinFrame] = []
    with httpx.Client(timeout=timeout_s) as client:
        for i in range(count):
            t0 = time.monotonic()
            try:
                r = client.get(f"{url.rstrip('/')}/api")
                if r.status_code != 200:
                    frames.append(
                        TwinFrame(time.time(), False, [f"HTTP {r.status_code}"], body=r.text)
                    )
                else:
                    frames.append(frame_from_body(r.text, time.time()))
            except httpx.HTTPError as e:
                frames.append(TwinFrame(time.time(), False, [f"{type(e).__name__}: {e}"]))
            if i < count - 1:
                time.sleep(max(0.0, interval_s - (time.monotonic() - t0)))
    return frames
