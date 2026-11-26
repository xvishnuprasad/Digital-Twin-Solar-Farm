"""Virtual ADC bus: physical quantities -> raw 12-bit codes on GPIO 34/35/32/33.

Two transfer models:
  * ``ideal``  - exactly the transfer the firmware assumes (inverse of its calibration):
                 V = raw/4095*10 and I = (raw/4095*5 - 2.5)/0.185.
  * ``esp32``  - physically faithful: 3.3 V ADC full scale with the ESP32's soft knee and
                 saturation near 3.1 V; voltage dividers scale 10 V -> 3.3 V; the ACS712
                 output (2.5 V + 0.185 V/A) optionally divided 5 V -> 3.3 V (``acs_divider``).
"""

from __future__ import annotations

import numpy as np

from .config import Scenario

PIN_A, PIN_B, PIN_C, PIN_D = 34, 35, 32, 33
PIN_OF = {"A": PIN_A, "B": PIN_B, "C": PIN_C, "D": PIN_D}
ADC_MAX = 4095

ACS_OFFSET_V = 2.5
ACS_SENS_V_PER_A = 0.185
V_FULL_SCALE = 10.0  # divider input that maps to ADC full scale (firmware assumption)
ESP32_VREF = 3.3
ESP32_KNEE_LO = 0.10  # below this the ESP32 ADC reads 0
ESP32_SAT_V = 3.10  # ~where readings pin at 4095 (11 dB attenuation)


def ideal_voltage_raw(v: float) -> float:
    return v / V_FULL_SCALE * ADC_MAX


def ideal_current_raw(i: float) -> float:
    return (ACS_OFFSET_V + ACS_SENS_V_PER_A * i) / 5.0 * ADC_MAX


def esp32_pin_raw(v_pin: float) -> float:
    """Approximate ESP32 ADC transfer (11 dB): dead zone, mild bow, hard saturation."""
    if v_pin <= ESP32_KNEE_LO:
        return 0.0
    x = (min(v_pin, ESP32_SAT_V) - ESP32_KNEE_LO) / (ESP32_SAT_V - ESP32_KNEE_LO)
    return ADC_MAX * (x + 0.03 * x * (1 - x))  # ~+0.75% bow mid-scale


def esp32_voltage_raw(v: float) -> float:
    return esp32_pin_raw(v * ESP32_VREF / V_FULL_SCALE)


def esp32_current_raw(i: float, divider: bool) -> float:
    v_out = ACS_OFFSET_V + ACS_SENS_V_PER_A * i
    return esp32_pin_raw(v_out * (ESP32_VREF / 5.0 if divider else 1.0))


def _rng(sc: Scenario, t_ms: int, pin: int) -> np.random.Generator:
    return np.random.default_rng([sc.seed, int(t_ms), pin])


def to_raw(sc: Scenario, truth: dict, t_ms: int) -> dict[int, int]:
    """Map physical truth to raw ADC codes, applying sensor/ADC faults and noise."""
    t_s = t_ms / 1000.0
    values = {"A": truth["V_A"], "B": truth["V_B"], "C": truth["V_C"], "D": truth["I_D"]}
    out: dict[int, int] = {}
    for name, val in values.items():
        pin = PIN_OF[name]
        rng = _rng(sc, t_ms, pin)
        stuck = saturated = None
        for f in sc.faults:
            if not (f.active(t_s) and f.hits(name)):
                continue
            if f.kind == "sensor_noise" and f.value > 0:
                val = val + rng.normal(0.0, f.value)
            elif f.kind == "sensor_stuck":
                stuck = int(f.value)
            elif f.kind == "adc_saturation":
                saturated = True
        if name == "D":
            val = max(val, -5.0)
            raw = (
                ideal_current_raw(val)
                if sc.adc_model == "ideal"
                else esp32_current_raw(val, sc.acs_divider)
            )
        else:
            val = max(val, 0.0)
            raw = ideal_voltage_raw(val) if sc.adc_model == "ideal" else esp32_voltage_raw(val)
        if sc.adc_noise_lsb > 0:
            raw += rng.normal(0.0, sc.adc_noise_lsb)
        code = int(np.clip(round(raw), 0, ADC_MAX))
        if saturated:
            code = ADC_MAX
        if stuck is not None:
            code = int(np.clip(stuck, 0, ADC_MAX))
        out[pin] = code
    return out
