"""CLI: ``uv run python -m sim <command>``.

serve     run the ESP32 emulator (+ mock Blynk + control panel) in real time
generate  write datasets (kaggle | rig)
bench     measure real-time tick jitter
poll      run the Unreal-Engine reference poller against an /api endpoint
replay    serve a recorded session (/recording JSONL) back as /api
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from .config import Scenario


def cmd_serve(a: argparse.Namespace) -> None:
    from .emulator import ServerThread
    from .engine import Clock, Engine

    sc = Scenario.load(a.scenario)
    eng = Engine(sc, backend=a.backend, clock=Clock("realtime", a.speed))
    with ServerThread(eng, host=a.host, port=a.port) as srv:
        print(f"emulator: {srv.url}/api   control panel: {srv.url}/control   backend={a.backend}")
        print(f"web UI: open index.html and set the ESP32 IP to {a.host}:{srv.port}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def cmd_generate(a: argparse.Namespace) -> None:
    from .datasets import generate_kaggle, generate_rig_log

    if a.kind == "kaggle":
        t0 = time.perf_counter()
        truth = generate_kaggle(a.out, days=a.days, inverters=a.inverters, seed=a.seed)
        print(f"wrote {truth['files']} to {a.out} in {time.perf_counter() - t0:.2f}s")
    else:
        sc = Scenario.load(a.scenario)
        if a.seed is not None:
            sc.seed = a.seed
        n = generate_rig_log(sc, a.out, ticks=a.ticks, backend=a.backend)
        print(f"wrote {n} ticks to {a.out}")


def cmd_bench(a: argparse.Namespace) -> None:
    from .engine import Clock, Engine

    eng = Engine(Scenario.load(a.scenario), clock=Clock("realtime"))
    eng.start(poll_s=0.002)
    time.sleep(a.seconds)
    eng.stop()
    j = sorted(eng.jitter_ms)
    if not j:
        sys.exit("no ticks recorded")
    p99 = j[min(len(j) - 1, int(0.99 * len(j)))]
    print(json.dumps({"ticks": len(j), "max_ms": round(j[-1], 2), "p99_ms": round(p99, 2),
                      "mean_ms": round(statistics.fmean(j), 2)}))  # fmt: skip


def cmd_poll(a: argparse.Namespace) -> None:
    from .ue_poller import poll

    for f in poll(a.url, a.interval, a.count):
        print(json.dumps({"ok": f.ok, "hud": f.hud, "errors": f.errors}))


def cmd_replay(a: argparse.Namespace) -> None:
    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    from .firmware_model import FirmwareModel

    rows = [json.loads(ln) for ln in Path(a.recording).read_text().splitlines() if ln.strip()]
    if not rows:
        sys.exit("empty recording")
    model, t0 = FirmwareModel(), time.monotonic()
    app = FastAPI()

    @app.get("/api")
    def api():
        t = (time.monotonic() - t0) * 1000 * a.speed
        idx = min(range(len(rows)), key=lambda i: abs(rows[i]["t_ms"] - rows[0]["t_ms"] - t))
        raws = {int(k): v for k, v in rows[idx]["raws"].items()}
        model.tick(rows[idx]["t_ms"], raws)
        r = model.api(rows[idx]["t_ms"], raws)
        return JSONResponse(json.loads(r.body), headers={"Access-Control-Allow-Origin": "*"})

    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m sim", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="run the emulator in real time")
    s.add_argument("--scenario", default="clear_day")
    s.add_argument("--backend", choices=["python", "fil"], default="python")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8080)
    s.add_argument("--speed", type=float, default=1.0, help="sim seconds per wall second")
    s.set_defaults(fn=cmd_serve)

    g = sub.add_parser("generate", help="write datasets")
    g.add_argument("kind", choices=["kaggle", "rig"])
    g.add_argument("--out", required=True)
    g.add_argument("--days", type=int, default=34)
    g.add_argument("--inverters", type=int, default=22)
    g.add_argument("--seed", type=int)
    g.add_argument("--scenario", default="clear_day")
    g.add_argument("--ticks", type=int)
    g.add_argument("--backend", choices=["python", "fil"], default="python")
    g.set_defaults(fn=cmd_generate)

    b = sub.add_parser("bench", help="real-time tick jitter")
    b.add_argument("--seconds", type=float, default=60)
    b.add_argument("--scenario", default="clear_day")
    b.set_defaults(fn=cmd_bench)

    q = sub.add_parser("poll", help="Unreal-Engine reference poller")
    q.add_argument("--url", default="http://127.0.0.1:8080")
    q.add_argument("--interval", type=float, default=2.0)
    q.add_argument("--count", type=int, default=5)
    q.set_defaults(fn=cmd_poll)

    r = sub.add_parser("replay", help="serve a /recording JSONL as /api")
    r.add_argument("recording")
    r.add_argument("--host", default="127.0.0.1")
    r.add_argument("--port", type=int, default=8080)
    r.add_argument("--speed", type=float, default=1.0)
    r.set_defaults(fn=cmd_replay)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
