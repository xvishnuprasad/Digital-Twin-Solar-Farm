"""Dataset generators: Kaggle schema, ground truth, rig logs, performance (criterion 7)."""

import json
import time

import pandas as pd
import pytest

from sim.config import Scenario
from sim.datasets import GEN_FILE, TRUTH_FILE, WEATHER_FILE, generate_kaggle, generate_rig_log

GEN_COLS = [
    "DATE_TIME",
    "PLANT_ID",
    "SOURCE_KEY",
    "DC_POWER",
    "AC_POWER",
    "DAILY_YIELD",
    "TOTAL_YIELD",
]
WEATHER_COLS = [
    "DATE_TIME",
    "PLANT_ID",
    "SOURCE_KEY",
    "AMBIENT_TEMPERATURE",
    "MODULE_TEMPERATURE",
    "IRRADIATION",
]


@pytest.fixture(scope="module")
def kaggle(tmp_path_factory):
    out = tmp_path_factory.mktemp("kaggle")
    t0 = time.perf_counter()
    truth = generate_kaggle(out, days=34, inverters=22, seed=42)
    return out, truth, time.perf_counter() - t0


@pytest.mark.covers("HARN-DATA", "FEAT-ML")
def test_kaggle_schema_and_shape(kaggle):
    out, truth, _ = kaggle
    gen, w = pd.read_csv(out / GEN_FILE), pd.read_csv(out / WEATHER_FILE)
    assert list(gen.columns) == GEN_COLS and list(w.columns) == WEATHER_COLS
    assert len(gen) == 34 * 96 * 22 and len(w) == 34 * 96
    assert gen.SOURCE_KEY.nunique() == 22 and (gen.PLANT_ID == 4136001).all()
    assert pd.to_datetime(gen.DATE_TIME).dt.minute.isin([0, 15, 30, 45]).all()
    assert (
        w.IRRADIATION.between(0, 1.3).all()
        and (w.MODULE_TEMPERATURE >= w.AMBIENT_TEMPERATURE - 1).all()
    )
    assert (
        json.loads((out / TRUTH_FILE).read_text())["inverter_efficiency"]
        == truth["inverter_efficiency"]
    )


@pytest.mark.covers("HARN-DATA", "FEAT-ML")
def test_kaggle_physical_consistency(kaggle):
    out, truth, _ = kaggle
    gen = pd.read_csv(out / GEN_FILE, parse_dates=["DATE_TIME"])
    day = gen[gen.DC_POWER > 0]
    ratio = day.AC_POWER / day.DC_POWER
    assert ratio.mean() == pytest.approx(truth["inverter_efficiency"], abs=0.002)
    assert (gen.AC_POWER <= gen.DC_POWER + 1e-9).all()
    night = gen[gen.DATE_TIME.dt.hour.isin([0, 1, 2, 3, 22, 23])]
    assert (night.DC_POWER == 0).all()
    for _, g in gen.groupby("SOURCE_KEY"):
        assert g.TOTAL_YIELD.is_monotonic_increasing
        first = g[g.DATE_TIME.dt.strftime("%H:%M") == "00:00"]
        assert (first.DAILY_YIELD < 1e-6).all()  # resets at midnight
        assert (
            g.groupby(g.DATE_TIME.dt.date)
            .DAILY_YIELD.apply(lambda s: s.is_monotonic_increasing)
            .all()
        )


@pytest.mark.covers("HARN-DATA")
def test_kaggle_generation_fast_and_deterministic(kaggle, tmp_path):
    out, _, elapsed = kaggle
    assert elapsed < 30
    generate_kaggle(tmp_path, days=34, inverters=22, seed=42)
    assert (tmp_path / GEN_FILE).read_bytes() == (out / GEN_FILE).read_bytes()


@pytest.mark.covers("HARN-DATA", "FEAT-MON", "FEAT-BLYNK", "FEAT-LED")
def test_rig_log(tmp_path):
    p = tmp_path / "rig.csv"
    n = generate_rig_log(Scenario.load("shading_and_degradation"), p, ticks=1800)
    df = pd.read_csv(p)
    assert n == len(df) == 1800
    assert df.t_ms.diff().dropna().eq(2000).all()
    shaded = df[(df.t_ms > 1_800_000) & (df.t_ms < 3_600_000)]
    assert (shaded.true_V_C < df.true_V_B.iloc[0]).all()
    assert (df[["led_14", "led_12", "led_13"]].sum(axis=1) == 1).all()  # one-hot AB group
