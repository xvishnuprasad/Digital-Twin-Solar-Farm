"""Shared fixtures + the feature-coverage report plugin.

Tag tests with ``@pytest.mark.covers("FEAT-API", ...)``. Known defects of the system under
test are encoded as ``pytest.mark.xfail(reason="F<n>: ...", strict=True)``; the fix PR for
F<n> removes the marker. At session end reports/coverage.{md,html} are written.
"""

from __future__ import annotations

import html
import re
from collections import defaultdict
from pathlib import Path

import pytest

from sim.config import Scenario
from sim.emulator import ServerThread
from sim.engine import Clock, Engine

REPO = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO / "reports"

FEATURES = {
    "FEAT-MON": "Real-time energy monitoring (V A/B/C, I D, 2 s sampling)",
    "FEAT-CAL": "Signal calibration formulas (12-bit ADC -> V / A)",
    "FEAT-CLS": "Three-state health classification (RED / YELLOW / GREEN)",
    "FEAT-LED": "Hardware LED status (2 groups x RGB)",
    "FEAT-SERIAL": "Serial debug log",
    "FEAT-API": "REST JSON API (GET /api)",
    "FEAT-BLYNK": "Blynk Cloud dashboard (V0-V5)",
    "FEAT-WEBUI": "Local IP web UI (index.html)",
    "FEAT-UE": "Unreal Engine 3D twin (REST contract)",
    "FEAT-ML": "ML power prediction notebook",
    "HARN-SCEN": "Harness: scenario engine, physics, faults, determinism",
    "HARN-DATA": "Harness: dataset generation (Kaggle schema, rig logs)",
    "HARN-V2": "Harness: N-panel farm mode (/api/v2)",
    "HARN-CTRL": "Harness: interactive control panel",
    "HARN-FIL": "Harness: firmware-in-the-loop differential testing",
}
DEFECT_RE = re.compile(r"\b(F\d+)\b")
_results: dict[str, list[tuple[str, str, str]]] = defaultdict(list)


def pytest_configure(config):
    config.addinivalue_line("markers", "covers(*features): README features this test verifies")
    config.addinivalue_line("markers", "slow: long-running (run with --run-slow)")
    config.addinivalue_line("markers", "ui: drives a browser via Playwright")
    config.addinivalue_line("markers", "fil: needs a host C++ compiler (firmware-in-the-loop)")


def pytest_addoption(parser):
    parser.addoption("--run-slow", action="store_true", help="run tests marked slow")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-slow"):
        return
    skip = pytest.mark.skip(reason="slow: use --run-slow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" or (rep.when == "setup" and rep.outcome != "passed"):
        if hasattr(rep, "wasxfail"):
            status = "xpass" if rep.outcome == "passed" else "xfail"
            note = rep.wasxfail
        else:
            status, note = rep.outcome, ""
            if rep.outcome == "skipped" and isinstance(rep.longrepr, tuple):
                note = rep.longrepr[2]
        marker = item.get_closest_marker("covers")
        for feat in marker.args if marker else ("UNMAPPED",):
            _results[feat].append((item.nodeid, status, note))


def pytest_sessionfinish(session, exitstatus):
    if not _results:
        return
    REPORT_DIR.mkdir(exist_ok=True)
    rows, defects = [], {}
    for feat, title in {
        **FEATURES,
        **({"UNMAPPED": "Tests without a covers() marker"} if "UNMAPPED" in _results else {}),
    }.items():
        res = _results.get(feat, [])
        n = defaultdict(int)
        for _, st, note in res:
            n[st] += 1
            if st in ("xfail", "xpass"):
                for d in DEFECT_RE.findall(note):
                    defects.setdefault(d, note)
        if n["failed"] or n["xpass"]:
            verdict = "FAIL"
        elif n["passed"]:
            verdict = "PASS" + (" (known defects)" if n["xfail"] else "")
        elif n["xfail"]:
            verdict = "DEFECT"
        else:
            verdict = "NOT RUN"
        rows.append(
            (feat, title, n["passed"], n["xfail"], n["failed"] + n["xpass"], n["skipped"], verdict)
        )
    md = ["# Feature coverage report", "", "| Feature | Description | Pass | Known defect (xfail) | Fail | Skipped | Verdict |",
          "|---|---|---:|---:|---:|---:|---|"]  # fmt: skip
    md += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | **{r[6]}** |" for r in rows]
    md += ["", "## Known defects in the system under test", "", "| ID | Detail |", "|---|---|"]
    md += [f"| {d} | {defects[d]} |" for d in sorted(defects, key=lambda x: int(x[1:]))] or [
        "| - | none |"
    ]
    md += ["", "## Tests by feature", ""]
    for feat in [r[0] for r in rows]:
        md.append(f"### {feat}")
        md += [f"- `{st}` {nid}" for nid, st, _ in _results.get(feat, [])] or ["- (none)"]
        md.append("")
    (REPORT_DIR / "coverage.md").write_text("\n".join(md))
    colour = {"PASS": "#16a34a", "FAIL": "#dc2626", "DEFECT": "#d97706", "NOT RUN": "#64748b"}
    trs = "".join(
        f"<tr><td>{r[0]}</td><td>{html.escape(r[1])}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td>"
        f"<td style='color:{colour[r[6].split(' (')[0]]};font-weight:700'>{r[6]}</td></tr>"
        for r in rows
    )
    dtr = "".join(
        f"<tr><td>{d}</td><td>{html.escape(defects[d])}</td></tr>"
        for d in sorted(defects, key=lambda x: int(x[1:]))
    )
    (REPORT_DIR / "coverage.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Feature coverage</title>"
        "<style>body{font:14px system-ui;margin:24px}table{border-collapse:collapse}td,th{border:1px solid #cbd5e1;padding:4px 8px}</style>"
        "<h1>Feature coverage</h1><table><tr><th>Feature</th><th>Description</th><th>Pass</th><th>xfail</th><th>Fail</th><th>Skip</th><th>Verdict</th></tr>"
        f"{trs}</table><h2>Known defects</h2><table><tr><th>ID</th><th>Detail</th></tr>{dtr}</table>"
    )


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def fil_exe():
    from sim.fil import FilError, build, compiler

    if not compiler():
        pytest.skip("no C++ compiler for firmware-in-the-loop")
    try:
        return build()
    except FilError as e:
        pytest.fail(str(e))


@pytest.fixture
def emulator():
    """Factory: start a real-time emulator server; stopped at teardown."""
    started: list[ServerThread] = []

    def _start(
        scenario: str | Scenario = "lab_bench", backend: str = "python", speed: float = 1.0, **net
    ):
        sc = Scenario.load(scenario) if isinstance(scenario, str) else scenario
        for k, v in net.items():
            setattr(sc.network, k, v)
        srv = ServerThread(Engine(sc, backend=backend, clock=Clock("realtime", speed)))
        srv.__enter__()
        started.append(srv)
        return srv

    yield _start
    for s in started:
        s.__exit__(None, None, None)


@pytest.fixture
def manual_engine():
    engines: list[Engine] = []

    def _make(scenario: str | Scenario = "lab_bench", backend: str = "python") -> Engine:
        sc = Scenario.load(scenario) if isinstance(scenario, str) else scenario
        e = Engine(sc, backend=backend)
        engines.append(e)
        return e

    yield _make
    for e in engines:
        e.stop()
