"""Bit-faithful Python port of Solar_Farm.ino (reference model).

Mirrors the firmware's float32 arithmetic and string formatting so its output can be
byte-compared against the real sketch running in the firmware-in-the-loop (FIL) harness.
Keep this file in sync with Solar_Farm.ino: tests/test_fil.py fails when they diverge.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .adc import PIN_A, PIN_B, PIN_C, PIN_D

RED_AB, YELLOW_AB, GREEN_AB = 14, 12, 13
RED_CD, YELLOW_CD, GREEN_CD = 25, 26, 27
LED_PINS = (RED_AB, YELLOW_AB, GREEN_AB, RED_CD, YELLOW_CD, GREEN_CD)

STATUS_RED = "RED: No Voltage"
STATUS_YELLOW = "YELLOW: Low Voltage"
STATUS_GREEN = "GREEN: Normal"

f32 = np.float32


def read_voltage(raw: int) -> float:
    # float voltage = (raw / 4095.0) * 10.0;
    return float(f32((raw / 4095.0) * 10.0))


def read_current(raw: int) -> float:
    # float voltage = (raw / 4095.0) * 5.0; float current = (voltage - 2.5) / 0.185;
    v = float(f32((raw / 4095.0) * 5.0))
    c = float(f32((v - 2.5) / 0.185))
    return 0.0 if c < 0 else c


def classify(v: float) -> str:
    if v <= 1.0:
        return STATUS_RED
    if v < 5.0:
        return STATUS_YELLOW
    return STATUS_GREEN


def led_levels(status: str, red: int, yellow: int, green: int) -> dict[int, int]:
    return {
        red: int(status == STATUS_RED),
        yellow: int(status == STATUS_YELLOW),
        green: int(status == STATUS_GREEN),
    }


def fmt2(x: float) -> str:
    """Arduino String(float, 2) / printf("%.2f") of a float promoted to double."""
    return f"{x:.2f}"


@dataclass
class HttpResponse:
    status: int
    content_type: str
    body: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class Events:
    blynk: list[tuple[int, object]] = field(default_factory=list)  # (virtual pin, value)
    leds: dict[int, int] = field(default_factory=dict)  # final level per GPIO
    serial: list[str] = field(default_factory=list)


class FirmwareModel:
    """Stateful model: statusAB/statusC persist between sendData() and handleAPI()."""

    name = "python"

    def __init__(self) -> None:
        self.status_ab = ""
        self.status_c = ""

    def setup(self) -> Events:
        ev = Events()  # setup() only calls pinMode(): no LED writes
        ev.serial = ["Connecting WiFi", "Wi-Fi Connected! IP: ", "127.0.0.1", "API Ready"]
        return ev

    def update_leds(self, va: float, vb: float, vc: float) -> dict[int, int]:
        combined_ab = float(f32(float(f32(f32(va) + f32(vb))) / 2.0))
        self.status_ab = classify(combined_ab)
        self.status_c = classify(vc)
        leds = led_levels(self.status_ab, RED_AB, YELLOW_AB, GREEN_AB)
        leds.update(led_levels(self.status_c, RED_CD, YELLOW_CD, GREEN_CD))
        return leds

    def tick(self, t_ms: int, raws: dict[int, int]) -> Events:
        """sendData(): fired by BlynkTimer every 2000 ms."""
        va, vb, vc = read_voltage(raws[PIN_A]), read_voltage(raws[PIN_B]), read_voltage(raws[PIN_C])
        cd = read_current(raws[PIN_D])
        ev = Events()
        ev.blynk = [(0, va), (1, vb), (2, vc), (3, cd)]
        ev.leds = self.update_leds(va, vb, vc)
        ev.blynk += [(4, self.status_ab), (5, self.status_c)]
        ev.serial = [
            f"A: {fmt2(va)} V | B: {fmt2(vb)} V | C: {fmt2(vc)} V | D Current: {fmt2(cd)} A"
        ]
        return ev

    def api(self, t_ms: int, raws: dict[int, int]) -> HttpResponse:
        """handleAPI(): re-reads the ADC and classifies those readings (not the last tick's)."""
        va, vb, vc = read_voltage(raws[PIN_A]), read_voltage(raws[PIN_B]), read_voltage(raws[PIN_C])
        cd = read_current(raws[PIN_D])
        status_ab = classify(float(f32(float(f32(f32(va) + f32(vb))) / 2.0)))
        status_c = classify(vc)
        body = (
            "{"
            f'"PanelA_Voltage":{fmt2(va)},'
            f'"PanelB_Voltage":{fmt2(vb)},'
            f'"PanelC_Voltage":{fmt2(vc)},'
            f'"PanelD_Current":{fmt2(cd)},'
            f'"Status_PanelAB":"{status_ab}",'
            f'"Status_PanelC":"{status_c}"'
            "}"
        )
        # server.sendHeader("Access-Control-Allow-Origin", "*") before server.send()
        return HttpResponse(200, "application/json", body, {"Access-Control-Allow-Origin": "*"})
