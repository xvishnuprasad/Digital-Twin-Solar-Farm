"""Unreal Engine twin, contract level: a reference poller standing in for the UE blueprint."""

import time

import pytest

from sim.ue_poller import COLOUR, frame_from_body, poll


@pytest.mark.covers("FEAT-UE", "FEAT-API")
@pytest.mark.parametrize("interval_s", [1.0, 2.0, 5.0])
def test_ue_poller_consistent_at_polling_cycles(emulator, interval_s):
    # speed=10: 1/2/5 s UE polling cycles of sim time in 0.1/0.2/0.5 s of wall time
    srv = emulator("cloudy_day", speed=10.0)
    while not srv.engine.history:  # wait for the first tick so the poll window is steady state
        time.sleep(0.01)
    frames = poll(srv.url, interval_s=interval_s / 10, count=6)
    assert all(f.ok for f in frames), [f.errors for f in frames]
    for f in frames:
        assert set(f.hud) == set(f.material) == {"A", "B", "C", "D"}
        assert all(c in COLOUR.values() for c in f.material.values())
        assert f.material["A"] == f.material["B"]  # AB share one LED group / material


@pytest.mark.covers("FEAT-UE")
def test_ue_poller_reports_transport_errors(emulator):
    srv = emulator("lab_bench")
    srv.engine.sc.network.mode = "http_500"
    frames = poll(srv.url, interval_s=0.05, count=2)
    assert not any(f.ok for f in frames) and frames[0].errors == ["HTTP 500"]


@pytest.mark.covers("FEAT-UE")
def test_ue_frame_rejects_contract_violations():
    assert not frame_from_body('{"PanelA_Voltage":1}', 0).ok
    assert not frame_from_body("{not json", 0).ok
    good = (
        '{"PanelA_Voltage":6.84,"PanelB_Voltage":6.81,"PanelC_Voltage":4.76,"PanelD_Current":1.01,'
        '"Status_PanelAB":"GREEN: Normal","Status_PanelC":"YELLOW: Low Voltage"}'
    )
    f = frame_from_body(good, 0)
    assert f.ok and f.hud["C"] == "4.76 V" and f.material["C"] == COLOUR["YELLOW"]
