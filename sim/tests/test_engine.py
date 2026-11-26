"""Engine: tick cadence, determinism, real-time behaviour, scenario catalogue."""

import itertools
import time

import pytest

from sim.config import SCENARIO_DIR, Scenario
from sim.contracts import check_v1_body
from sim.engine import Clock, Engine


def bodies(scenario: str, n: int, seed: int | None = None) -> list[str]:
    sc = Scenario.load(scenario)
    if seed is not None:
        sc.seed = seed
    e = Engine(sc)
    out = []
    for _ in range(n):
        e.step()
        out.append(e.api(e._manual_ms + 500).body)
    return out


@pytest.mark.covers("HARN-SCEN", "FEAT-UE")
def test_same_seed_replays_byte_identical():
    a, b = bodies("cloudy_day", 300), bodies("cloudy_day", 300)
    assert a == b
    assert bodies("cloudy_day", 300, seed=99) != a


@pytest.mark.covers("FEAT-MON", "FEAT-BLYNK")
def test_ticks_every_2000ms_of_sim_time(manual_engine):
    e = manual_engine("clear_day")
    e.step(10)
    assert [r.t_ms for r in e.history] == list(range(2000, 22000, 2000))
    v0 = e.blynk.history(0)
    assert [w.t_ms for w in v0] == list(range(2000, 22000, 2000))


@pytest.mark.covers("FEAT-MON")
def test_accelerated_full_day_is_fast(manual_engine):
    e = manual_engine("clear_day")
    t0 = time.perf_counter()
    e.step(21600)  # 12 h of 2-s ticks
    assert time.perf_counter() - t0 < 30
    statuses = {r.blynk[4][1] for r in e.history}
    assert "GREEN: Normal" in statuses


@pytest.mark.covers("HARN-SCEN", "FEAT-BLYNK")
def test_realtime_cadence_and_jitter():
    e = Engine(Scenario.load("lab_bench"), clock=Clock("realtime"))
    e.start(poll_s=0.005)
    time.sleep(8.5)
    e.stop()
    walls = [w.wall for w in e.blynk.history(0)]
    assert len(walls) == 4
    gaps = [b - a for a, b in itertools.pairwise(walls)]
    assert all(1.8 <= g <= 2.2 for g in gaps), gaps  # 2000 ms +/- 10 %
    assert max(e.jitter_ms) < 100


@pytest.mark.covers("HARN-SCEN", "FEAT-API")
@pytest.mark.parametrize("path", sorted(SCENARIO_DIR.glob("*.yaml")), ids=lambda p: p.stem)
def test_scenario_catalogue_runs_and_honours_contract(path):
    e = Engine(Scenario.load(path))
    e.step(60)
    for t in range(0, 120_000, 10_000):
        e.advance_to(max(t, 2000))
    errs = check_v1_body(e.api().body)
    assert not errs, errs
