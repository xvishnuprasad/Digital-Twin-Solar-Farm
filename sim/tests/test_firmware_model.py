"""Reference model of Solar_Farm.ino: calibration, classification, formatting."""

import json

import pytest

from sim import firmware_model as fm
from sim.adc import PIN_A, PIN_B, PIN_C, PIN_D


@pytest.mark.covers("FEAT-CAL")
@pytest.mark.parametrize("raw,volts", [(0, 0.0), (4095, 10.0), (2048, 5.0012), (409, 0.9988)])
def test_voltage_formula(raw, volts):
    assert fm.read_voltage(raw) == pytest.approx(volts, abs=1e-4)


@pytest.mark.covers("FEAT-CAL")
@pytest.mark.parametrize(
    "raw,amps", [(2047, 0.0), (2048, 0.0033), (3000, 6.2866), (4095, 13.5135), (0, 0.0)]
)
def test_current_formula_and_negative_clamp(raw, amps):
    assert fm.read_current(raw) == pytest.approx(amps, abs=1e-3)


@pytest.mark.covers("FEAT-CLS")
@pytest.mark.parametrize(
    "v,status",
    [
        (0.0, fm.STATUS_RED), (0.99, fm.STATUS_RED), (1.0, fm.STATUS_RED), (1.01, fm.STATUS_YELLOW),
        (4.99, fm.STATUS_YELLOW), (5.0, fm.STATUS_GREEN), (5.01, fm.STATUS_GREEN), (9.9, fm.STATUS_GREEN),
    ],
)  # fmt: skip
def test_classification_boundaries(v, status):
    assert fm.classify(v) == status


@pytest.mark.covers("FEAT-LED", "FEAT-CLS")
def test_leds_one_hot_per_group():
    m = fm.FirmwareModel()
    leds = m.update_leds(6.0, 6.0, 0.5)
    assert (leds[fm.RED_AB], leds[fm.YELLOW_AB], leds[fm.GREEN_AB]) == (0, 0, 1)
    assert (leds[fm.RED_CD], leds[fm.YELLOW_CD], leds[fm.GREEN_CD]) == (1, 0, 0)
    leds = m.update_leds(6.0, 2.0, 3.0)  # AB average 4.0 -> yellow
    assert (leds[fm.RED_AB], leds[fm.YELLOW_AB], leds[fm.GREEN_AB]) == (0, 1, 0)
    assert (leds[fm.RED_CD], leds[fm.YELLOW_CD], leds[fm.GREEN_CD]) == (0, 1, 0)


@pytest.mark.covers("FEAT-API", "FEAT-SERIAL", "FEAT-BLYNK")
def test_tick_and_api_payload_format():
    m = fm.FirmwareModel()
    raws = {PIN_A: 2800, PIN_B: 2790, PIN_C: 2770, PIN_D: 2200}
    ev = m.tick(2000, raws)
    assert [p for p, _ in ev.blynk] == [0, 1, 2, 3, 4, 5]
    assert ev.serial == ["A: 6.84 V | B: 6.81 V | C: 6.76 V | D Current: 1.01 A"]
    body = m.api(2500, raws).body
    assert body == (
        '{"PanelA_Voltage":6.84,"PanelB_Voltage":6.81,"PanelC_Voltage":6.76,"PanelD_Current":1.01,'
        '"Status_PanelAB":"GREEN: Normal","Status_PanelC":"GREEN: Normal"}'
    )
    assert list(json.loads(body)) == [
        "PanelA_Voltage", "PanelB_Voltage", "PanelC_Voltage", "PanelD_Current", "Status_PanelAB", "Status_PanelC",
    ]  # fmt: skip
