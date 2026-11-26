# Digital-Twin-Solar-Farm + simulation harness

Fork of `xvishnuprasad/Digital-Twin-Solar-Farm` (remote `upstream`). Our fork is `origin`.
Goal: a Python harness that simulates the ESP32 rig and verifies every consumer.
Architecture: `docs/SIMULATION_HARNESS.md`. Plan, criteria and status: `docs/SIMULATOR_PLAN.md`.

## Layout
- **System under test (SUT), repo root:** `Solar_Farm.ino` (ESP32 firmware: `GET /api`, Blynk V0–V5), `index.html` (web UI, polls `/api` every 2 s), `Untitled3.ipynb` (ML notebook, Kaggle Plant_2 CSVs).
- **Harness:** `sim/` (Python 3.12, uv). Tests are in `sim/tests/`. Scenarios are in `sim/scenarios/`. `sim/firmware_model.py` must stay in sync with `Solar_Farm.ino`; the FIL differential test enforces this.
- Media (`*.mp4`, `*.mov`) is demo footage. Never read it.

## Commands
- `uv sync` installs deps. `uv run ruff check --fix . && uv run ruff format .` lints and formats.
- `uv run playwright install chromium` if the browser is missing.
- `uv run pytest` runs the full suite and writes `reports/coverage.md`. `uv run pytest --run-slow` adds the arduino-cli ESP32 compile check. `-m "not ui"` skips the browser tests.
- `uv run python -m sim serve --scenario cloudy_day [--backend fil]` starts the emulator; the control panel is at `/control`.
- `uv run python -m sim generate kaggle --out data/kaggle` generates datasets.
- ESP32 compile check: arduino-cli requires the folder name to match the sketch name, so copy first:
  `d=$(mktemp -d)/Solar_Farm && mkdir -p $d && cp Solar_Farm.ino $d/ && { [ -f secrets.example.h ] && cp secrets.example.h $d/secrets.h; true; } && arduino-cli compile -b esp32:esp32:esp32 $d`

## Rules
- SUT files (`Solar_Farm.ino`, `index.html`, `Untitled3.ipynb`) change **only on `fix/*` branches**. Each fix is one defect per PR (F1–F9 in `docs/SIMULATION_HARNESS.md`). The fix removes that defect's `xfail(strict=True)` marker, and it must update `sim/firmware_model.py` whenever firmware behaviour changes. Harness work goes on other branches.
- Every new fault or scenario gets a YAML scenario, a test, and a row in the coverage report.
- Never commit credentials. Wi-Fi and Blynk values belong in a gitignored `secrets.h` or `.env`.
- The notebook is committed stripped (nbstripout git filter). To read it, run `nbstripout -t Untitled3.ipynb` and read that output, never the raw JSON.
- Commit or push only when asked. PRs go to `origin` (our fork) unless told otherwise.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. When the answer is under a Markdown heading, `graphify section "<heading>"` prints that section's text, so the .md need not be opened. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
