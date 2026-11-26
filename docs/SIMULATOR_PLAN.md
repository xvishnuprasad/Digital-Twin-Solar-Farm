# Solar Farm Digital Twin — Simulation & Verification Harness: Plan (Draft v1)

System under test (SUT): https://github.com/xvishnuprasad/Digital-Twin-Solar-Farm @ `38e9405`
Architecture: [`SIMULATION_HARNESS.md`](./SIMULATION_HARNESS.md)


## Delivery status (2026-11-22)

| Phase | Status | Where |
|---|---|---|
| 0. Foundation | ✅ Done | `pyproject.toml`, `.github/workflows/ci.yml`, `CLAUDE.md`, nbstripout filter |
| 1. Scenario & physics | ✅ Done | `sim/config.py`, `sim/physics.py`, `sim/scenarios/` |
| 2. ADC & reference model | ✅ Done | `sim/adc.py`, `sim/firmware_model.py` |
| 3. ESP32 emulator | ✅ Done | `sim/emulator.py`, `sim/blynk_mock.py`, `sim/contracts/` |
| 4. Firmware-in-the-loop | ✅ Done | `sim/fil/` (unmodified sketch, 10 000-vector differential test) |
| 5. Dataset generator | ✅ Done | `sim/datasets.py` |
| 6. Verification suite | ✅ Done | `sim/tests/`, `reports/coverage.md` |
| 7. Control panel | ✅ Done | `sim/static/control.html` at `/control` |
| 8. SUT fix PRs | ✅ Opened | F1, F2, F5, F6 (firmware, stacked), F7+F8 (notebook), F9 (web UI); F3 and F4 open by design |
| Later | ⏳ | Real Blynk adapter, UE project, hardware-in-the-loop comparison |

Defaults taken for the open questions in §8: PRs go to the fork; both ACS712 wirings are modelled; `/api/v2` is emulator-only; Kaggle Plant_2 location (17.4 N, 78.5 E, IST); GitHub Actions CI.

---

## 1. Refined prompt

> Build a **Python simulation & verification harness** for the Digital-Twin-Solar-Farm system that can stand in for the physical ESP32 rig, so every feature of the monitoring system can be tested **without hardware or cloud accounts**.
>
> The harness must:
> 1. Model the physical inputs (sun irradiance, clouds, temperature, per-panel shading and faults, sensor noise and ADC behaviour) from a **declarative YAML scenario** with a seed, running in **real-time (2 s ticks)** or **accelerated or batch** mode.
> 2. Exercise the system at **two layers**:
>    - **Firmware-in-the-loop:** compile the *unmodified* `Solar_Farm.ino` on the host against an Arduino/WebServer/Blynk shim whose `analogRead()` is fed by the simulator.
>    - **ESP32 emulator:** a pure-Python service that serves the same `GET /api` contract, a serial log stream and Blynk V0–V5 writes.
> 3. Support the **legacy 4-panel rig** (exact current JSON schema) and an opt-in **N-panel farm mode** (`/api/v2`, versioned schema).
> 4. Feed and verify **all consumers**: the local web UI (`index.html`, via Playwright), Blynk (via a mock Blynk service), the Unreal Engine twin (via contract tests and a reference polling client, since the UE project is not available) and the ML notebook (generated CSVs in the Kaggle *Plant_2 Generation + Weather Sensor* schema).
> 5. Provide an **automated scenario suite with a per-feature pass/fail coverage report**, plus an **interactive control panel** for live fault injection, both driven by the same scenario engine.
> 6. Treat defects found in the SUT as findings: encode them as expected-fail tests and fix each in its own reviewable PR.

---

## 2. Intent / Goals / Objectives

**Intent.** Turn a hardware-dependent demo into a system whose behaviour can be checked repeatably, from sensor to dashboard, on any laptop or CI runner.

| # | Goal | Objective (measurable) |
|---|------|------------------------|
| G1 | Hardware independence | Every README feature can be tested with no ESP32, no Wi-Fi, no Blynk account and no UE install. |
| G2 | Fidelity | Simulated ADC → firmware → `/api` values match the physics ground truth within the firmware's own quantisation (±0.0025 V, ±0.0066 A) plus configured noise. |
| G3 | Firmware truth | The real `.ino` logic is exercised. The Python emulator is differential-tested against it and must agree on 100% of 10 000 random ADC vectors (±0.01). |
| G4 | Consumer coverage | Web UI, Blynk, UE contract and ML notebook each have automated checks driven by shared scenarios. |
| G5 | Realistic datasets | Seeded, reproducible time-series and CSV datasets with known ground truth (e.g. inverter efficiency), usable as-is by the notebook. |
| G6 | Exploratory testing | An operator can inject faults live and watch every consumer react. |

---

## 3. Success criteria (Definition of Done)

1. **Contract:** a JSON Schema for `/api` v1 (6 keys, 2-decimal floats, 3 status strings) is published. The emulator and the firmware-in-the-loop both pass it, and `/api/v2` is documented and versioned.
2. **Classification:** boundary tests at 0.99 / 1.00 / 1.01 / 4.99 / 5.00 / 5.01 V, for both the AB average and C, check the status strings **and** the six LED GPIO states. Pass rate: 100%.
3. **Web UI (Playwright, headless):** for each scenario, the displayed values, LED colours and the *Connected/Disconnected* indicator are correct within ≤ 2 poll cycles (≤ 4 s). This includes network drop, HTTP 500, malformed JSON, missing keys and slow responses.
4. **Blynk (mock):** V0–V5 receive writes every 2000 ms ± 10%, with values equal to the same tick's sample.
5. **UE (contract only, for now):** a reference poller at 1 s / 2 s / 5 s sees consistent, schema-valid data. Replay of a scenario with the same seed is byte-identical.
6. **ML:** generated CSVs load in the notebook unchanged (only the path edited), and the notebook runs end-to-end via papermill. Its AC/DC efficiency estimate recovers the configured efficiency within ±1%.
7. **Determinism and performance:** same config + seed gives identical output. 34 days × 22 inverters × 15 min generates in < 30 s. Real-time tick jitter is < 100 ms over 1 h.
8. **Coverage report:** an HTML or Markdown matrix maps every README feature to ≥ 1 passing scenario. Known SUT defects show as `xfail` with a link to their fix PR.
9. **Control panel:** sliders and toggles for irradiance, per-panel shading or disconnect, sensor noise, ADC saturation, network latency/drop and CORS on/off. Changes appear in `/api` within one tick.

---

## 4. Findings from code review (feed the test plan)

| # | Area | Finding | Simulator test |
|---|------|---------|----------------|
| F1 | Web UI ↔ firmware | The firmware sends **no CORS header**. `index.html` (opened as `file://` or from another origin) fetches `http://<ip>/api`, so browsers will likely block reading the response. | Emulator CORS toggle; Playwright asserts the UI state with CORS on and off. |
| F2 | Firmware | `handleAPI()` re-reads the ADC but returns `statusAB/statusC` from the **last `sendData()`**, so the status can disagree with the voltages for up to 2 s. Before the first tick, the status strings are `""` and the UI shows OFF. | Step-change scenario; assert voltage/status consistency. Cold-start test. |
| F3 | Firmware | Panel B is never classified on its own (the AB average can hide a dead B). The CD LED uses only C, and D's current is never classified. | "Panel B dead, A healthy" scenario yields avg ≈ 3.45 V, which shows YELLOW, not a B fault. |
| F4 | Firmware / HW | The current formula assumes 0–5 V on the ADC, but the ESP32 ADC tops out at about 3.3 V (and `analogRead` is non-linear above about 3.1 V). Unless the ACS712 output is divided down, readings are off. | Two ADC models: "firmware-assumed" and "physically faithful". Compare the results. **Needs wiring confirmation.** |
| F5 | Firmware | `setup()` blocks forever if Wi-Fi is down. There is no reconnect handling. | Emulator boot-without-network scenario (FIL shim). |
| F6 | Security | **Wi-Fi SSID and password are committed** in `Solar_Farm.ino`. | Move to `secrets.h` (gitignored) in the fix PR. Rotate the password. |
| F7 | Notebook | Cell 3 loads the **generation CSV as `weather_data`**, so the `_x/_y` columns are duplicates. The "irradiation" and "ambient temperature" plots actually plot DC power. The model's `*_y` features exist only because of this bug. | Generator ships the real weather schema. The fix PR must also redefine the features. |
| F8 | Notebook | `r2_score(y_pred, y_test)` has its arguments reversed. `DATE`/`TIME` columns are used but no visible cell creates them. The paths are hard-coded to Google Drive. | papermill run in CI. Generator emits `DATE`/`TIME` columns or the fix PR derives them. |
| F9 | Web UI | `fetch` has no timeout, so a hung ESP32 never flips the UI to Disconnected. `toFixed` on a missing key throws and is silently reported as "Disconnected". | Slow-response and missing-key scenarios. |

---

## 5. Architecture

```
            scenario.yaml (seed, site, panels, weather, faults, network, time mode)
                                   │
                    ┌──────────────▼───────────────┐
                    │  Scenario & Physics Engine    │  pvlib clear-sky + cloud model,
                    │  (sim/core)                   │  temperature, shading, faults
                    └──────┬──────────────┬────────┘
                ground truth│              │ ADC model (noise, non-linearity, clipping)
                           │      ┌────────▼─────────┐
                           │      │ Virtual ADC bus   │  raw 0–4095 per GPIO 34/35/32/33
                           │      └───┬──────────┬───┘
            ┌──────────────┘          │          │
            │            ┌────────────▼──┐  ┌────▼──────────────────────┐
            │            │ ESP32 Emulator │  │ Firmware-in-the-loop       │
            │            │ (Python/FastAPI)│ │ Solar_Farm.ino + C++ shim  │
            │            │ /api, /api/v2,  │ │ (Arduino, WebServer, Blynk,│
            │            │ serial, Blynk   │ │  Serial, GPIO), g++ build  │
            │            └──┬─────┬────┬──┘  └──┬──────┬──────┬──────────┘
            │   net-fault proxy (latency/drop/500/CORS)       │
            │               │     │    └─────► Mock Blynk ◄───┘
            │               ▼     ▼                 ▲
            │        index.html  UE reference poller │
            │        (Playwright)(contract tests)    │
            ▼
   Dataset Generator → Kaggle-schema CSVs → papermill(notebook) → assertions
            │
   Coverage report + Control Panel (web UI, live scenario mutation)
```

**Stack:** Python 3.12 (managed by uv), pydantic (config schema), pvlib + numpy/pandas, FastAPI/uvicorn, httpx, pytest + pytest-playwright, papermill/nbclient, C++17 shim built with g++/clang (CMake). The control panel is FastAPI with HTMX or a small vanilla JS page.

---

## 6. Phased delivery

| Phase | Deliverable | Exit check |
|-------|-------------|------------|
| 0. Foundation | Fork/branch, `uv` project, CI skeleton, notebook outputs stripped (`nbstripout`), `CLAUDE.md` pointing at the graphify report, F6 secrets PR | CI green on an empty test |
| 1. Scenario & physics | YAML schema, seeded engine, real-time and accelerated clocks, fault library (disconnect, shading, degradation, sensor stuck/noisy, ADC saturation) | Determinism test; clear-sky curve sanity |
| 2. ADC & reference model | Inverse calibration, two ADC models (F4), Python port of the firmware logic | Boundary tests (criterion 2) on the reference model |
| 3. ESP32 emulator | `/api` v1, `/api/v2` (N panels), serial stream, mock Blynk, network-fault proxy, CORS toggle | Contract tests (criterion 1), Blynk cadence (criterion 4) |
| 4. Firmware-in-the-loop | C++ shim that builds the *unmodified* `.ino`, ADC fed from the sim, LED states reported back | Differential test vs Phase 2 (G3) |
| 5. Dataset generator | Kaggle generation and weather CSVs, rig logs, Blynk-history export, ground-truth sidecar JSON | papermill run + efficiency recovery (criterion 6); performance (criterion 7) |
| 6. Verification suite | Playwright web-UI tests, UE reference poller and contract tests, scenario catalogue, coverage report | Criteria 3, 5, 8 |
| 7. Control panel | Live sliders and toggles, scenario record/replay | Criterion 9 |
| 8. SUT fix PRs | F1, F2, F5, F7–F9 fixes, each one turning an xfail into a pass | All xfails resolved or accepted |
| Later | Real Blynk (HTTP API token), real UE project, physical rig hardware-in-the-loop comparison | Plug-in adapters; no core changes |

---

## 7. Decisions recorded

- Layers: **both** (emulator + firmware-in-the-loop)
- Consumers: **Web UI, Blynk, UE, ML** (Blynk and UE are mocked or contract-tested until access exists)
- Scale: **legacy 4-panel + configurable N-panel** behind `/api/v2`
- Verification: **automated suite + interactive control panel**
- SUT defects: **report as xfail, fix in separate PRs**
- Access: **none yet** (no Blynk token, UE project or rig)
- Time: **real-time + accelerated**
- Stack: **Python**

## 8. Open questions (defaults assumed if unanswered)

1. **Where do PRs go?** Is this the upstream repo (you're a collaborator), a fork under your account, or a new standalone repo with the SUT as a git submodule? *Default: fork + harness in a separate `sim/` folder of the fork.*
2. **ACS712 wiring (F4):** is the sensor output divided down to 3.3 V before GPIO 33? *Default: model both.*
3. **N-panel mode:** should `index.html` and UE be upgraded to `/api/v2`, or does v2 only serve new consumers? *Default: v2 is emulator-only; no consumer changes.*
4. **Site and weather realism:** a specific location or timezone for the solar curve? *Default: the Kaggle Plant_2 location (India, UTC+5:30), May–June.*
5. **CI target:** GitHub Actions? *Default: yes, Ubuntu runner.*
