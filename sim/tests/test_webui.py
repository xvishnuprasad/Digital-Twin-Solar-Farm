"""index.html driven headlessly by Playwright against the real-time emulator.

The page is opened from file:// (as the README instructs) and pointed at the emulator via
its ESP32-IP field. UI logic tests force the CORS header on so they test the UI itself;
F1 tests exercise the firmware's real header behaviour.
"""

import json

import httpx
import pytest
from playwright.sync_api import Page, expect

from sim.conftest_helpers import INDEX_HTML

pytestmark = pytest.mark.ui
POLL = 2000  # index.html polls every 2 s
WITHIN = 2 * POLL + 500  # success criterion: <= 2 poll cycles


def connect(page: Page, srv) -> None:
    page.goto(INDEX_HTML.as_uri())
    ip = page.locator("#espIP")
    ip.fill(f"127.0.0.1:{srv.port}")
    ip.dispatch_event("change")


def control(srv, **patch) -> None:
    httpx.post(f"{srv.url}/control", json=patch).raise_for_status()


@pytest.mark.covers("FEAT-WEBUI", "FEAT-MON", "FEAT-CLS")
def test_ui_shows_live_values_and_green_leds(page: Page, emulator):
    srv = emulator("lab_bench", cors=True)
    connect(page, srv)
    expect(page.locator("#connectionStatus")).to_have_text("Connected", timeout=WITHIN)
    api = json.loads(httpx.get(f"{srv.url}/api").text)
    expect(page.locator("#voltageA")).to_have_text(f"{api['PanelA_Voltage']:.2f} V", timeout=WITHIN)
    expect(page.locator("#currentD")).to_have_text(f"{api['PanelD_Current']:.2f} A", timeout=WITHIN)
    expect(page.locator("#ledAB")).to_have_text("GREEN", timeout=WITHIN)
    expect(page.locator("#ledC")).to_have_text("GREEN")
    expect(page.locator("#statusABText")).to_have_text("GREEN: Normal")
    expect(page.locator("#lastUpdateAB")).not_to_have_text("Last update: --")


@pytest.mark.covers("FEAT-WEBUI", "FEAT-CLS")
def test_ui_yellow_then_red_as_panels_fail(page: Page, emulator):
    srv = emulator("lab_bench", cors=True)
    connect(page, srv)
    expect(page.locator("#ledAB")).to_have_text("GREEN", timeout=WITHIN)
    control(srv, faults=[{"kind": "disconnect", "target": "B"}])
    expect(page.locator("#ledAB")).to_have_text("YELLOW", timeout=WITHIN + POLL)
    control(srv, faults=[{"kind": "disconnect", "target": t} for t in "ABC"])
    expect(page.locator("#ledAB")).to_have_text("RED", timeout=WITHIN + POLL)
    expect(page.locator("#ledC")).to_have_text("RED", timeout=WITHIN + POLL)
    expect(page.locator("#voltageC")).to_have_text("0.00 V")


@pytest.mark.covers("FEAT-WEBUI", "FEAT-CLS")
def test_ui_night_scenario_all_red(page: Page, emulator):
    srv = emulator("night", cors=True)
    connect(page, srv)
    expect(page.locator("#ledAB")).to_have_text("RED", timeout=WITHIN + POLL)
    expect(page.locator("#ledC")).to_have_text("RED")


@pytest.mark.covers("FEAT-WEBUI")
@pytest.mark.parametrize("mode", ["http_500", "malformed_json", "missing_keys", "down"])
def test_ui_flags_bad_responses_as_disconnected(page: Page, emulator, mode):
    srv = emulator("lab_bench", cors=True)
    connect(page, srv)
    expect(page.locator("#connectionStatus")).to_have_text("Connected", timeout=WITHIN)
    control(srv, network={"mode": mode})
    expect(page.locator("#connectionStatus")).to_contain_text("Disconnected", timeout=WITHIN)
    control(srv, network={"mode": "ok"})
    expect(page.locator("#connectionStatus")).to_have_text("Connected", timeout=WITHIN)


@pytest.mark.covers("FEAT-WEBUI")
def test_ui_detects_hung_device(page: Page, emulator):
    srv = emulator("lab_bench", cors=True)
    connect(page, srv)
    expect(page.locator("#connectionStatus")).to_have_text("Connected", timeout=WITHIN)
    control(srv, network={"mode": "hang", "hang_s": 30})
    expect(page.locator("#connectionStatus")).to_have_text("Disconnected", timeout=3 * POLL)


@pytest.mark.covers("FEAT-WEBUI")
def test_ui_tolerates_slow_link(page: Page, emulator):
    srv = emulator("network_flaky", cors=True)  # 800 ms latency
    connect(page, srv)
    expect(page.locator("#connectionStatus")).to_have_text("Connected", timeout=WITHIN)
    expect(page.locator("#ledAB")).to_have_text("GREEN", timeout=WITHIN)


@pytest.mark.covers("FEAT-WEBUI")
def test_ui_persists_esp_ip(page: Page, emulator):
    srv = emulator("lab_bench", cors=True)
    connect(page, srv)
    page.reload()
    expect(page.locator("#espIP")).to_have_value(f"127.0.0.1:{srv.port}")
    expect(page.locator("#connectionStatus")).to_have_text("Connected", timeout=WITHIN)


@pytest.mark.covers("FEAT-WEBUI", "FEAT-API")
def test_ui_works_with_firmware_default_headers(page: Page, emulator):
    srv = emulator("lab_bench")  # cors=None: headers exactly as the firmware model sends them
    connect(page, srv)
    expect(page.locator("#connectionStatus")).to_have_text("Connected", timeout=WITHIN)


@pytest.mark.fil
@pytest.mark.covers("FEAT-WEBUI", "HARN-FIL")
def test_ui_works_against_real_firmware(page: Page, emulator, fil_exe):
    srv = emulator("lab_bench", backend="fil")
    connect(page, srv)
    expect(page.locator("#connectionStatus")).to_have_text("Connected", timeout=WITHIN)
