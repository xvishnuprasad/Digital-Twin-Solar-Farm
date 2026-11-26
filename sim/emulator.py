"""ESP32 emulator HTTP service (FastAPI).

Routes
  GET  /api            firmware contract v1 (served by the selected firmware backend)
  GET  /api/v2         N-panel farm contract (emulator-only)
  GET  /state          live engine state (truth, raw ADC, LEDs, serial, Blynk)
  POST /control        mutate the running scenario (irradiance, faults, network, ADC)
  GET  /control        interactive control panel (HTML)
  GET  /serial         recent Serial Monitor lines
  GET  /recording      tick history as JSON Lines (record / replay)
  GET  /blynk/...      mock Blynk Cloud HTTP API
"""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from pathlib import Path
from typing import Self

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

from .config import Fault, Network
from .engine import Engine

STATIC = Path(__file__).parent / "static"
FAULTABLE = ("/api", "/api/v2")


def _cors(engine: Engine, headers: dict[str, str], default_on: bool) -> dict[str, str]:
    cors = engine.sc.network.cors
    h = dict(headers)
    if cors is True or (cors is None and default_on):
        h["Access-Control-Allow-Origin"] = "*"
    elif cors is False:
        h.pop("Access-Control-Allow-Origin", None)
    return h


def create_app(engine: Engine) -> FastAPI:
    app = FastAPI(title="Solar Farm ESP32 emulator", docs_url="/docs")
    app.state.engine = engine

    @app.middleware("http")
    async def network_faults(request: Request, call_next):
        net = engine.sc.network
        if request.url.path not in FAULTABLE or net.mode == "ok":
            return await call_next(request)
        if net.mode == "latency":
            await asyncio.sleep(net.latency_ms / 1000)
            return await call_next(request)
        if net.mode == "hang":
            await asyncio.sleep(net.hang_s)
            return await call_next(request)
        if net.mode == "http_500":
            return PlainTextResponse(
                "Internal Server Error", status_code=500, headers=_cors(engine, {}, True)
            )
        if net.mode == "down":
            return PlainTextResponse("Service Unavailable", status_code=503)
        resp = await call_next(request)
        body = b"".join([c async for c in resp.body_iterator])
        if net.mode == "malformed_json":
            body = body[: max(1, len(body) // 2)]
        elif net.mode == "missing_keys" and request.url.path == "/api":
            data = json.loads(body)
            data.pop("PanelD_Current", None)
            body = json.dumps(data, separators=(",", ":")).encode()
        headers = {k: v for k, v in resp.headers.items() if k.lower() != "content-length"}
        return Response(
            body, status_code=resp.status_code, headers=headers, media_type=resp.media_type
        )

    @app.get("/api")
    def api() -> Response:
        r = engine.api()
        headers = _cors(engine, r.headers, default_on=False)  # None = faithful to firmware
        return Response(r.body, status_code=r.status, media_type=r.content_type, headers=headers)

    @app.get("/api/v2")
    def api_v2() -> JSONResponse:
        return JSONResponse(engine.api_v2(), headers=_cors(engine, {}, default_on=True))

    @app.get("/state")
    def state() -> dict:
        t = engine.now_ms()
        engine.advance_to(t)
        return {
            "t_ms": t,
            "backend": engine.backend_kind,
            "truth": engine.truth(t),
            "raws": engine.raws(t),
            "leds": engine.leds,
            "serial": list(engine.serial)[-20:],
            "blynk": engine.blynk.datastreams(),
            "scenario": {
                "name": engine.sc.name,
                "irradiance_override": engine.sc.weather.irradiance_override,
                "faults": [f.model_dump() for f in engine.sc.faults],
                "network": engine.sc.network.model_dump(),
                "adc_model": engine.sc.adc_model,
                "acs_divider": engine.sc.acs_divider,
                "adc_noise_lsb": engine.sc.adc_noise_lsb,
            },
        }

    @app.post("/control")
    async def control(request: Request) -> dict:
        patch = await request.json()
        with engine.lock:
            sc = engine.sc
            if "irradiance_override" in patch:
                v = patch["irradiance_override"]
                sc.weather.irradiance_override = None if v is None else float(v)
            if "faults" in patch:
                sc.faults = [Fault.model_validate(f) for f in patch["faults"]]
            if "add_fault" in patch:
                sc.faults.append(Fault.model_validate(patch["add_fault"]))
            if "network" in patch:
                sc.network = Network.model_validate({**sc.network.model_dump(), **patch["network"]})
            for key in ("adc_model", "acs_divider", "adc_noise_lsb"):
                if key in patch:
                    setattr(sc, key, patch[key])
        return {"ok": True, "t_ms": engine.now_ms()}

    @app.get("/", response_class=HTMLResponse)
    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard() -> str:
        return (Path(__file__).resolve().parent.parent / "index.html").read_text()

    @app.get("/control", response_class=HTMLResponse)
    def control_panel() -> str:
        return (STATIC / "control.html").read_text()

    @app.get("/serial", response_class=PlainTextResponse)
    def serial() -> str:
        return "\n".join(engine.serial)

    @app.get("/recording")
    def recording() -> Response:
        lines = [
            json.dumps(
                {"t_ms": r.t_ms, "truth": r.truth, "raws": r.raws, "leds": r.leds, "blynk": r.blynk}
            )
            for r in list(engine.history)
        ]
        return PlainTextResponse("\n".join(lines), media_type="application/x-ndjson")

    # ---- mock Blynk Cloud (subset of https://docs.blynk.io HTTP API) ----
    def _token_ok(token: str | None) -> bool:
        return token == engine.blynk.token

    @app.get("/blynk/external/api/get")
    def blynk_get(request: Request, token: str | None = None) -> Response:
        if not _token_ok(token):
            return PlainTextResponse("Invalid token.", status_code=400)
        pins = [k for k in request.query_params if k.startswith("V")]
        data = engine.blynk.datastreams()
        if len(pins) == 1:
            return PlainTextResponse(str(data.get(pins[0], "")))
        return JSONResponse({p: data.get(p) for p in pins} if pins else data)

    @app.get("/blynk/external/api/isHardwareConnected")
    def blynk_connected(token: str | None = None) -> Response:
        if not _token_ok(token):
            return PlainTextResponse("Invalid token.", status_code=400)
        return PlainTextResponse("true" if engine.blynk.writes else "false")

    @app.get("/blynk/history")
    def blynk_history(pin: int = 0) -> list[dict]:
        return [
            {"t_ms": w.t_ms, "wall": w.wall, "value": w.value} for w in engine.blynk.history(pin)
        ]

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return (
            "<h1>Solar Farm ESP32 emulator</h1><ul>"
            '<li><a href="/api">/api</a></li><li><a href="/api/v2">/api/v2</a></li>'
            '<li><a href="/control">/control</a> (control panel)</li>'
            '<li><a href="/state">/state</a></li><li><a href="/docs">/docs</a></li></ul>'
        )

    return app


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ServerThread:
    """Run the emulator in a background thread (used by tests and the CLI)."""

    def __init__(self, engine: Engine, host: str = "127.0.0.1", port: int | None = None):
        self.engine = engine
        self.host, self.port = host, port or free_port()
        cfg = uvicorn.Config(
            create_app(engine),
            host=self.host,
            port=self.port,
            log_level="warning",
            timeout_graceful_shutdown=1,
        )
        self.server = uvicorn.Server(cfg)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def __enter__(self) -> Self:
        self.engine.start()
        self.thread.start()
        deadline = time.monotonic() + 10
        while not self.server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("emulator did not start")
            time.sleep(0.02)
        return self

    def __exit__(self, *exc) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)
        self.engine.stop()
