# Graph Report - Digital-Twin-Solar-Farm-main 2  (2026-11-26)

## Corpus Check
- 55 files · ~23,154 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 5, .ipynb 1, .log 1)

## Summary
- 662 nodes · 1309 edges · 37 communities (27 shown, 10 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 108 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- 🌞 Digital Twin Renewable Energy Solar Farm
- Scenario
- test_fil.py
- Solar_Farm.ino
- Engine
- json
- test_emulator.py
- test_webui.py
- emulator.py
- test_notebook.py
- steps
- WebServer
- shim.cpp
- String
- farm_n_panels.yaml
- panel_b_disconnect.yaml
- sensor_faults.yaml
- shading_and_degradation.yaml
- BlynkTimer
- cloudy_day.yaml
- lab_bench.yaml
- network_flaky.yaml
- BlynkWifi
- esp32_adc_physical.yaml
- WiFiClass
- clear_day.yaml
- night.yaml
- Digital-Twin-Solar-Farm + simulation harness
- Arduino.h
- main.cpp
- solar-twin-sim

## God Nodes (most connected - your core abstractions)
1. `Scenario` - 40 edges
2. `Engine` - 38 edges
3. `WebServer` - 21 edges
4. `create_app()` - 20 edges
5. `generate_kaggle()` - 20 edges
6. `Environment` - 17 edges
7. `FirmwareModel` - 16 edges
8. `FilFirmware` - 16 edges
9. `client()` - 15 edges
10. `🌞 Digital Twin Renewable Energy Solar Farm` - 14 edges

## Surprising Connections (you probably didn't know these)
- `2. Components` --references--> `ServerThread`  [INFERRED]
  docs/SIMULATION_HARNESS.md → sim/emulator.py
- `Tier 1 — Embedded Firmware (`Solar_Farm.ino`)` --references--> `BlynkTimer`  [INFERRED]
  README.md → sim/fil/include/BlynkSimpleEsp32.h
- `classifyVoltage()` --references--> `String`  [EXTRACTED]
  Solar_Farm.ino → sim/fil/include/Arduino.h
- `2. Components` --references--> `Farm`  [INFERRED]
  docs/SIMULATION_HARNESS.md → sim/config.py
- `2. Components` --references--> `Fault`  [INFERRED]
  docs/SIMULATION_HARNESS.md → sim/config.py

## Import Cycles
- None detected.

## Communities (37 total, 10 thin omitted)

### Community 0 - "🌞 Digital Twin Renewable Energy Solar Farm"
Cohesion: 0.06
Nodes (31): 1. Flash Firmware, 2. Configure Credentials, 3. Set Up Blynk Dashboard, 4. Open Local Web UI, 5. Connect Unreal Engine, 🎥 Demonstration Videos, 🌞 Digital Twin Renewable Energy Solar Farm, End-to-End Architecture Diagram (+23 more)

### Community 1 - "Scenario"
Cohesion: 0.05
Nodes (40): 2. Components, Fault library, esp32_current_raw(), esp32_pin_raw(), esp32_voltage_raw(), ideal_current_raw(), ideal_voltage_raw(), _rng() (+32 more)

### Community 2 - "test_fil.py"
Cohesion: 0.06
Nodes (34): make_backend(), build(), compiler(), FilError, FilFirmware, FilProcess, FilTimeout, parse_events() (+26 more)

### Community 3 - "Solar_Farm.ino"
Cohesion: 0.07
Nodes (26): 1. Layered architecture, 3. Contracts, 4. Verification strategy, 5. Findings register, 6. Running it, 7. Assumptions and limits, Data flow per firmware tick, Simulation & Verification Harness: Architecture (+18 more)

### Community 4 - "Engine"
Cohesion: 0.06
Nodes (19): BlynkMock, BlynkWrite, ServerThread, Clock, Engine, run(), TickRecord, emulator() (+11 more)

### Community 6 - "json"
Cohesion: 0.17
Nodes (12): cmd_bench(), cmd_generate(), cmd_poll(), cmd_replay(), cmd_serve(), main(), test_ue_frame_rejects_contract_violations(), test_ue_poller_consistent_at_polling_cycles() (+4 more)

### Community 7 - "test_emulator.py"
Cohesion: 0.16
Nodes (14): check_v1_body(), errors(), schema(), validate(), client(), test_api_cold_start_has_valid_status(), test_api_v1_contract(), test_api_v2_contract_and_panel_faults() (+6 more)

### Community 8 - "test_webui.py"
Cohesion: 0.19
Nodes (14): api(), test_control_panel_drives_emulator(), wait_api(), connect(), control(), test_ui_detects_hung_device(), test_ui_flags_bad_responses_as_disconnected(), test_ui_night_scenario_all_red() (+6 more)

### Community 9 - "emulator.py"
Cohesion: 0.10
Nodes (9): _cors(), create_app(), api(), api_v2(), blynk_connected(), blynk_get(), network_faults(), _token_ok() (+1 more)

### Community 10 - "test_notebook.py"
Cohesion: 0.16
Nodes (7): code(), data_dir(), test_notebook_r2_argument_order(), test_notebook_reads_weather_csv(), test_notebook_runs_and_recovers_inverter_efficiency(), test_secrets_template_present_and_real_file_ignored(), test_sketch_has_no_inline_credentials()

### Community 11 - "steps"
Cohesion: 0.11
Nodes (18): jobs, test, name, on, pull_request, push, branches, if (+10 more)

### Community 12 - "WebServer"
Cohesion: 0.14
Nodes (6): WebServer, headers_, pending_, port_, routes_, WebServer::handleClient()

### Community 13 - "shim.cpp"
Cohesion: 0.17
Nodes (6): HardwareSerial, digitalWrite(), emit(), flush_serial(), HardwareSerial::print(), HardwareSerial::printf()

### Community 14 - "String"
Cohesion: 0.17
Nodes (4): IPAddress, String, s, WebServer::send()

### Community 15 - "farm_n_panels.yaml"
Cohesion: 0.14
Nodes (13): description, duration_s, farm, n_panels, faults, kind, target, value (+5 more)

### Community 16 - "panel_b_disconnect.yaml"
Cohesion: 0.14
Nodes (13): description, duration_s, faults, kind, start_s, target, name, start (+5 more)

### Community 17 - "sensor_faults.yaml"
Cohesion: 0.15
Nodes (12): description, duration_s, faults, end_s, kind, start_s, target, value (+4 more)

### Community 18 - "shading_and_degradation.yaml"
Cohesion: 0.15
Nodes (12): description, duration_s, faults, end_s, kind, start_s, target, value (+4 more)

### Community 19 - "BlynkTimer"
Cohesion: 0.22
Nodes (6): BlynkTimer, T, interval, prev, timers_, millis()

### Community 20 - "cloudy_day.yaml"
Cohesion: 0.20
Nodes (9): adc_noise_lsb, description, duration_s, name, start, weather, cloud_model, cloud_persistence_s (+1 more)

### Community 21 - "lab_bench.yaml"
Cohesion: 0.20
Nodes (9): description, duration_s, name, start, weather, ambient_max_c, ambient_min_c, cloud_model (+1 more)

### Community 22 - "network_flaky.yaml"
Cohesion: 0.20
Nodes (9): description, duration_s, name, network, latency_ms, mode, start, weather (+1 more)

### Community 23 - "BlynkWifi"
Cohesion: 0.28
Nodes (3): BlynkWifi, configured_, delay()

### Community 24 - "esp32_adc_physical.yaml"
Cohesion: 0.22
Nodes (8): acs_divider, adc_model, description, duration_s, name, start, weather, cloud_model

### Community 26 - "clear_day.yaml"
Cohesion: 0.29
Nodes (6): description, duration_s, name, start, weather, cloud_model

### Community 27 - "night.yaml"
Cohesion: 0.29
Nodes (6): description, duration_s, name, start, weather, cloud_model

### Community 28 - "Digital-Twin-Solar-Farm + simulation harness"
Cohesion: 0.33
Nodes (5): Commands, Digital-Twin-Solar-Farm + simulation harness, graphify, Layout, Rules

## Knowledge Gaps
- **10 isolated node(s):** `solar-twin-sim`, `headers_`, `pending_`, `port_`, `routes_` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 296 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Simulation & Verification Harness: Architecture` connect `Solar_Farm.ino` to `Scenario`?**
  _High betweenness centrality (0.262) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `Scenario` (e.g. with `2. Components` and `_rng()`) actually correct?**
  _`Scenario` has 23 INFERRED edges - model-reasoned connections that need verification._
- **What connects `solar-twin-sim`, `headers_`, `pending_` to the rest of the system?**
  _10 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `🌞 Digital Twin Renewable Energy Solar Farm` be split into smaller, more focused modules?**
  _Cohesion score 0.06451612903225806 - nodes in this community are weakly interconnected._
- **Why does `2. Components` connect `Scenario` to `Solar_Farm.ino`, `Engine`?**
  _High betweenness centrality (0.261) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Engine` (e.g. with `export_blynk_history()` and `BlynkMock`) actually correct?**
  _`Engine` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `Scenario` be split into smaller, more focused modules?**
  _Cohesion score 0.05306217858812529 - nodes in this community are weakly interconnected._