"""ESP32 emulator HTTP service: contracts, network faults, CORS, control, mock Blynk."""

import json
import warnings

import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient

from sim.config import Scenario
from sim.contracts import check_v1_body, errors
from sim.emulator import create_app
from sim.engine import Engine


def client(scenario="lab_bench", ticks=1, **net) -> tuple[TestClient, Engine]:
    sc = Scenario.load(scenario)
    for k, v in net.items():
        setattr(sc.network, k, v)
    e = Engine(sc)
    e.step(ticks)
    return TestClient(create_app(e)), e


@pytest.mark.covers("FEAT-API", "FEAT-UE")
def test_api_v1_contract():
    c, _ = client()
    r = c.get("/api")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")
    assert check_v1_body(r.text) == []


@pytest.mark.covers("FEAT-API", "FEAT-UE")
def test_api_cold_start_has_valid_status():
    c, _ = client(ticks=0)
    assert check_v1_body(c.get("/api").text) == []


@pytest.mark.covers("HARN-V2")
def test_api_v2_contract_and_panel_faults():
    c, _ = client("farm_n_panels")
    d = c.get("/api/v2").json()
    assert errors(d, "v2") == []
    by_id = {p["id"]: p for p in d["panels"]}
    assert len(by_id) == 16
    assert by_id["P12"]["status"] == "RED" and by_id["P12"]["voltage"] == 0
    assert by_id["P7"]["voltage"] < by_id["P3"]["voltage"] < by_id["P1"]["voltage"]


@pytest.mark.covers("FEAT-API")
@pytest.mark.parametrize("cors,expected", [(None, "*"), (True, "*"), (False, None)])
def test_cors_toggle(cors, expected):
    c, _ = client(cors=cors)
    assert c.get("/api").headers.get("access-control-allow-origin") == expected


@pytest.mark.covers("FEAT-API", "FEAT-UE")
def test_network_fault_modes():
    c, e = client()
    e.sc.network.mode = "http_500"
    assert c.get("/api").status_code == 500
    e.sc.network.mode = "down"
    assert c.get("/api").status_code == 503
    e.sc.network.mode = "malformed_json"
    with pytest.raises(json.JSONDecodeError):
        json.loads(c.get("/api").text)
    e.sc.network.mode = "missing_keys"
    assert "PanelD_Current" not in c.get("/api").json()
    e.sc.network.mode = "ok"
    assert check_v1_body(c.get("/api").text) == []


@pytest.mark.covers("HARN-CTRL", "FEAT-CLS")
def test_control_endpoint_mutates_live_scenario():
    c, e = client()
    c.post("/control", json={"add_fault": {"kind": "disconnect", "target": "B"}})
    e.step()
    assert (
        c.get("/api").json()["Status_PanelAB"] == "YELLOW: Low Voltage"
    )  # F3: dead B only -> YELLOW
    c.post("/control", json={"irradiance_override": 0, "faults": []})
    e.step()
    d = c.get("/api").json()
    assert d["Status_PanelAB"] == d["Status_PanelC"] == "RED: No Voltage"
    s = c.get("/state").json()
    assert s["leds"]["14"] == 1 and s["leds"]["25"] == 1
    c.post("/control", json={"network": {"mode": "http_500"}})
    assert c.get("/api").status_code == 500


@pytest.mark.covers("FEAT-BLYNK")
def test_mock_blynk_http_api():
    c, e = client(ticks=3)
    tok = e.blynk.token
    assert c.get("/blynk/external/api/get", params={"token": "bad", "V0": ""}).status_code == 400
    assert float(c.get(f"/blynk/external/api/get?token={tok}&V0").text) == pytest.approx(
        json.loads(c.get("/api").text)["PanelA_Voltage"], abs=0.01
    )
    assert c.get(f"/blynk/external/api/get?token={tok}&V4").text == "GREEN: Normal"
    allv = c.get(f"/blynk/external/api/get?token={tok}").json()
    assert set(allv) == {f"V{i}" for i in range(6)}
    assert c.get(f"/blynk/external/api/isHardwareConnected?token={tok}").text == "true"
    assert [h["t_ms"] for h in c.get("/blynk/history?pin=5").json()] == [2000, 4000, 6000]


@pytest.mark.covers("FEAT-SERIAL")
def test_serial_and_recording():
    c, _ = client(ticks=2)
    lines = c.get("/serial").text.splitlines()
    assert "API Ready" in lines and lines[-1].startswith("A: ")
    rec = [json.loads(ln) for ln in c.get("/recording").text.splitlines()]
    assert [r["t_ms"] for r in rec] == [2000, 4000]


@pytest.mark.covers("FEAT-BLYNK", "FEAT-UE")
def test_blynk_values_match_tick_sample():
    _, e = client(scenario="cloudy_day", ticks=50)
    for rec in e.history:
        b = dict(rec.blynk)
        assert b[0] == pytest.approx(rec.raws[34] / 4095 * 10, abs=1e-5)
