"""Dataset generators.

* Kaggle "Solar Power Generation Data" schema (Plant_2_Generation_Data.csv and
  Plant_2_Weather_Sensor_Data.csv) for the ML notebook, plus a ground-truth sidecar.
* Rig telemetry logs (truth, raw ADC, firmware outputs) from an accelerated engine run.
* Blynk V0-V5 history export.
"""

from __future__ import annotations

import csv
import json
import string
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Scenario
from .engine import Engine
from .physics import ambient_temp, clearsky_ghi, cloud_index, module_temp

GEN_FILE = "Plant_2_Generation_Data.csv"
WEATHER_FILE = "Plant_2_Weather_Sensor_Data.csv"
TRUTH_FILE = "ground_truth.json"
SLOT_MIN = 15


def _keys(rng: np.random.Generator, n: int) -> list[str]:
    alphabet = np.array(list(string.ascii_letters + string.digits))
    return ["".join(rng.choice(alphabet, 15)) for _ in range(n)]


def generate_kaggle(
    out_dir: str | Path,
    days: int = 34,
    inverters: int | None = None,
    seed: int | None = None,
    scenario: Scenario | None = None,
    start: datetime = datetime(2020, 5, 15),
) -> dict:
    """Write the two Kaggle-schema CSVs and ground_truth.json; return the ground truth."""
    sc = scenario or Scenario()
    if seed is not None:
        sc = sc.model_copy(update={"seed": seed})
    farm = sc.farm
    n_inv = inverters or farm.inverters
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng([sc.seed, 2020])

    n_slots = days * 24 * 60 // SLOT_MIN
    times = pd.date_range(start, periods=n_slots, freq=f"{SLOT_MIN}min", tz=sc.site.tz)
    ghi = clearsky_ghi(times, sc) * cloud_index(n_slots, SLOT_MIN * 60, sc)
    irr_kw = ghi / 1000.0
    t_amb = ambient_temp(times, sc) + rng.normal(0, 0.3, n_slots)
    t_mod = module_temp(t_amb, ghi, sc.panel.noct)

    caps = farm.dc_kw_per_inverter * (
        1 + rng.uniform(-farm.capacity_spread, farm.capacity_spread, n_inv)
    )
    keys = _keys(rng, n_inv)
    base_total = rng.uniform(1.0e8, 2.5e9, n_inv)
    temp_factor = 1 + farm.temp_coeff * (t_mod - 25.0)
    dc = (
        caps[None, :]
        * irr_kw[:, None]
        * temp_factor[:, None]
        * rng.uniform(0.97, 1.0, (n_slots, n_inv))
    )
    dc[rng.random((n_slots, n_inv)) < farm.outage_rate] = 0.0
    dc = np.clip(dc, 0.0, None)
    eff = farm.inverter_efficiency + rng.normal(0, farm.efficiency_noise, (n_slots, n_inv))
    ac = dc * np.clip(eff, 0.0, 1.0)

    energy = ac * SLOT_MIN / 60.0  # kWh per slot
    day_idx = np.asarray((times - times[0]).days)
    daily = np.zeros_like(energy)
    for d in np.unique(day_idx):
        m = day_idx == d
        daily[m] = np.cumsum(energy[m], axis=0)
    total = base_total[None, :] + np.cumsum(energy, axis=0)

    naive = times.tz_localize(None)
    gen = pd.DataFrame(
        {
            "DATE_TIME": np.repeat(naive.strftime("%Y-%m-%d %H:%M:%S"), n_inv),
            "PLANT_ID": farm.plant_id,
            "SOURCE_KEY": np.tile(keys, n_slots),
            "DC_POWER": dc.ravel().round(6),
            "AC_POWER": ac.ravel().round(6),
            "DAILY_YIELD": daily.ravel().round(6),
            "TOTAL_YIELD": total.ravel().round(3),
        }
    )
    weather = pd.DataFrame(
        {
            "DATE_TIME": naive.strftime("%Y-%m-%d %H:%M:%S"),
            "PLANT_ID": farm.plant_id,
            "SOURCE_KEY": _keys(rng, 1)[0],
            "AMBIENT_TEMPERATURE": t_amb.round(6),
            "MODULE_TEMPERATURE": np.asarray(t_mod).round(6),
            "IRRADIATION": irr_kw.round(6),
        }
    )
    gen.to_csv(out / GEN_FILE, index=False)
    weather.to_csv(out / WEATHER_FILE, index=False)
    truth = {
        "seed": sc.seed,
        "days": days,
        "inverters": n_inv,
        "slot_minutes": SLOT_MIN,
        "plant_id": farm.plant_id,
        "inverter_efficiency": farm.inverter_efficiency,
        "efficiency_noise": farm.efficiency_noise,
        "temp_coeff": farm.temp_coeff,
        "outage_rate": farm.outage_rate,
        "dc_kw_per_inverter": dict(zip(keys, caps.round(3).tolist())),
        "files": [GEN_FILE, WEATHER_FILE],
    }
    (out / TRUTH_FILE).write_text(json.dumps(truth, indent=2))
    return truth


RIG_COLUMNS = [
    "timestamp", "t_ms", "irradiance_wm2", "ambient_c", "module_c",
    "true_V_A", "true_V_B", "true_V_C", "true_I_D",
    "raw_34", "raw_35", "raw_32", "raw_33",
    "V0", "V1", "V2", "V3", "V4", "V5",
    "led_14", "led_12", "led_13", "led_25", "led_26", "led_27",
]  # fmt: skip


def generate_rig_log(
    scenario: Scenario, out_csv: str | Path, ticks: int | None = None, backend: str = "python"
) -> int:
    """Run the engine in accelerated mode and write one row per firmware tick."""
    eng = Engine(scenario, backend=backend)
    n = ticks or int(scenario.duration_s // scenario.tick_s)
    t0 = pd.Timestamp(scenario.start)
    out = Path(out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with out.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(RIG_COLUMNS)
            for _ in range(n):
                eng.step()
                r = eng.history[-1]
                b = dict(r.blynk)
                tr = r.truth
                w.writerow(
                    [
                        (t0 + timedelta(milliseconds=r.t_ms)).isoformat(), r.t_ms,
                        round(tr["irradiance_wm2"], 2), round(tr["ambient_c"], 2), round(tr["module_c"], 2),
                        round(tr["V_A"], 4), round(tr["V_B"], 4), round(tr["V_C"], 4), round(tr["I_D"], 4),
                        r.raws[34], r.raws[35], r.raws[32], r.raws[33],
                        *(b.get(i) for i in range(6)),
                        *(r.leds.get(p, 0) for p in (14, 12, 13, 25, 26, 27)),
                    ]
                )  # fmt: skip
    finally:
        eng.stop()
    return n


def export_blynk_history(engine: Engine, out_csv: str | Path) -> int:
    rows = [(w.t_ms, f"V{w.pin}", w.value) for w in engine.blynk.writes]
    with Path(out_csv).open("w", newline="") as fh:
        csv.writer(fh).writerows([("t_ms", "pin", "value"), *rows])
    return len(rows)
