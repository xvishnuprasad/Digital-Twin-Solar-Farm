"""Interactive control panel (criterion 9): UI changes reach /api within one tick."""

import json

import httpx
import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.ui
ONE_TICK = 2000 + 1500  # tick + control-panel refresh


def api(srv) -> httpx.Response:
    return httpx.get(f"{srv.url}/api")


def wait_api(page: Page, srv, pred, timeout_ms=ONE_TICK) -> dict:
    deadline = timeout_ms / 1000
    import time

    t0 = time.monotonic()
    while True:
        r = api(srv)
        if r.status_code == 200 and pred(json.loads(r.text)):
            return json.loads(r.text)
        if time.monotonic() - t0 > deadline:
            raise AssertionError(f"/api did not reach expected state: {r.text}")
        page.wait_for_timeout(100)


@pytest.mark.covers("HARN-CTRL", "FEAT-CLS", "FEAT-LED")
def test_control_panel_drives_emulator(page: Page, emulator):
    srv = emulator("lab_bench")
    page.goto(f"{srv.url}/control")
    expect(page.locator("#meta")).to_contain_text("lab_bench", timeout=3000)
    expect(page.locator("#l13")).to_have_class("led g on", timeout=ONE_TICK)  # AB green

    page.locator("#dcB").check()
    page.locator("#applyFaults").click()
    wait_api(page, srv, lambda d: d["Status_PanelAB"].startswith("YELLOW"))
    expect(page.locator("#l12")).to_have_class("led y on", timeout=ONE_TICK)

    page.locator("#irr").fill("0")
    page.locator("#ovOn").check()
    wait_api(page, srv, lambda d: d["Status_PanelC"].startswith("RED") and d["PanelA_Voltage"] == 0)
    expect(page.locator("#l25")).to_have_class("led r on", timeout=ONE_TICK)

    page.locator("#netMode").select_option("http_500")
    page.locator("#applyNet").click()
    expect(page.locator("#api")).to_contain_text("HTTP 500", timeout=ONE_TICK)
    assert api(srv).status_code == 500

    page.locator("#netMode").select_option("ok")
    page.locator("#applyNet").click()
    page.locator("#clearFaults").click()
    page.locator("#ovOn").uncheck()
    wait_api(page, srv, lambda d: d["Status_PanelAB"].startswith("GREEN"))
