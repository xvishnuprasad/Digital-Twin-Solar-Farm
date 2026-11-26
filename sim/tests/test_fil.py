"""Firmware-in-the-loop: the real Solar_Farm.ino vs the Python reference model (goal G3)."""

import json

import numpy as np
import pytest

from sim.adc import PIN_A, PIN_B, PIN_C, PIN_D
from sim.contracts import check_v1_body
from sim.fil import FilFirmware, FilTimeout
from sim.firmware_model import (
    GREEN_AB,
    GREEN_CD,
    RED_AB,
    RED_CD,
    YELLOW_AB,
    YELLOW_CD,
    FirmwareModel,
)

pytestmark = pytest.mark.fil


@pytest.fixture
def fil(fil_exe):
    f = FilFirmware(fil_exe)
    f.setup()
    yield f
    f.close()


def raws(a, b, c, d):
    return {PIN_A: a, PIN_B: b, PIN_C: c, PIN_D: d}


def assert_same(ev_fil, ev_py):
    assert ev_fil.leds == ev_py.leds
    assert ev_fil.serial == ev_py.serial
    assert [p for p, _ in ev_fil.blynk] == [p for p, _ in ev_py.blynk]
    for (_, vf), (_, vp) in zip(ev_fil.blynk, ev_py.blynk):
        if isinstance(vp, str):
            assert vf == vp
        else:
            assert vf == pytest.approx(vp, rel=1e-6, abs=1e-7)


@pytest.mark.covers("HARN-FIL", "FEAT-SERIAL")
def test_fil_setup(fil_exe):
    f = FilFirmware(fil_exe)
    try:
        ev = f.setup()
        assert ev.serial == FirmwareModel().setup().serial
    finally:
        f.close()


@pytest.mark.covers(
    "HARN-FIL", "FEAT-CAL", "FEAT-CLS", "FEAT-LED", "FEAT-API", "FEAT-BLYNK", "FEAT-SERIAL"
)
def test_fil_differential_10000_random_vectors(fil):
    model = FirmwareModel()
    model.setup()
    rng = np.random.default_rng(2024)
    vecs = rng.integers(0, 4096, size=(10_000, 4))
    # bias a quarter of the vectors onto the classification thresholds
    vecs[::4, :3] = rng.choice([408, 409, 410, 411, 2046, 2047, 2048, 2049], size=(2500, 3))
    for i, (a, b, c, d) in enumerate(vecs):
        r = raws(int(a), int(b), int(c), int(d))
        t = 2000 * (i + 1)
        assert_same(fil.tick(t, r), model.tick(t, r))
        rf, rp = fil.api(t + 500, r), model.api(t + 500, r)
        assert (rf.status, rf.content_type, rf.body, rf.headers) == (
            rp.status,
            rp.content_type,
            rp.body,
            rp.headers,
        )


@pytest.mark.covers("HARN-FIL", "FEAT-CLS", "FEAT-LED")
@pytest.mark.parametrize(
    "a,b,c,ab_led,c_led",
    [
        (409, 409, 409, "R", "R"),  # 0.9988 V -> RED
        (410, 410, 410, "Y", "Y"),  # 1.0012 V -> YELLOW
        (2047, 2047, 2047, "Y", "Y"),  # 4.9988 V -> YELLOW
        (2048, 2048, 2048, "G", "G"),  # 5.0012 V -> GREEN
        (4095, 0, 4095, "G", "G"),  # AB average exactly 5.00 V -> GREEN
        (4093, 1, 0, "Y", "R"),  # AB average 4.9988 V -> YELLOW
        (819, 0, 2048, "R", "G"),  # AB average 1.00 V -> RED (<= 1.0)
    ],
)  # fmt: skip
def test_fil_threshold_boundaries(fil, a, b, c, ab_led, c_led):
    ev = fil.tick(2000, raws(a, b, c, 2048))
    order = "RYG"
    ab = [ev.leds[p] for p in (RED_AB, YELLOW_AB, GREEN_AB)]
    cd = [ev.leds[p] for p in (RED_CD, YELLOW_CD, GREEN_CD)]
    assert ab == [int(order[i] == ab_led) for i in range(3)]
    assert cd == [int(order[i] == c_led) for i in range(3)]


@pytest.mark.covers("FEAT-API", "FEAT-WEBUI")
def test_fil_api_sends_cors_header(fil):
    fil.tick(2000, raws(2800, 2800, 2800, 2200))
    assert (
        fil.api(2500, raws(2800, 2800, 2800, 2200)).headers.get("Access-Control-Allow-Origin")
        == "*"
    )


@pytest.mark.covers("FEAT-API", "FEAT-UE")
def test_fil_cold_start_status(fil):
    assert check_v1_body(fil.api(100, raws(2800, 2800, 2800, 2200)).body) == []


@pytest.mark.covers("FEAT-API", "FEAT-CLS")
def test_fil_status_consistent_with_voltages(fil):
    fil.tick(2000, raws(2800, 2800, 2800, 2200))  # GREEN
    d = json.loads(fil.api(2100, raws(100, 100, 100, 2048)).body)  # panels just went dark
    assert d["PanelA_Voltage"] < 1 and d["Status_PanelAB"] == "RED: No Voltage"


@pytest.mark.covers("FEAT-MON", "FEAT-API")
def test_fil_boots_without_wifi(fil_exe):
    f = FilFirmware(fil_exe, wifi=False, timeout_s=1.5)
    try:
        ev = f.setup()  # bounded wait: millis() reaches ~15 s inside setup()
        assert any("offline" in ln for ln in ev.serial)
        tick = f.tick(20_000, raws(2800, 2800, 2800, 2200))
        assert tick.leds and not tick.blynk  # LEDs still driven, Blynk writes dropped offline
        assert f.api(20_500, raws(2800, 2800, 2800, 2200)).status == 200
    except FilTimeout:
        pytest.fail("firmware hung in setup() with Wi-Fi down")
    finally:
        f.close()


@pytest.mark.covers("FEAT-CLS")
@pytest.mark.xfail(
    reason="F3: panel B is never classified on its own; a dead B with healthy A shows YELLOW",
    strict=True,
)
def test_fil_dead_panel_b_is_flagged(fil):
    fil.tick(2000, raws(2800, 0, 2800, 2200))
    d = json.loads(fil.api(2500, raws(2800, 0, 2800, 2200)).body)
    assert d["Status_PanelAB"].startswith("RED")
