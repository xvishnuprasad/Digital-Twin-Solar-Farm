"""Declarative scenario configuration (YAML <-> pydantic)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

SCENARIO_DIR = Path(__file__).parent / "scenarios"


class Site(BaseModel):
    """Location used for the solar geometry (default: Kaggle Plant_2 region, India)."""

    latitude: float = 17.4
    longitude: float = 78.5
    altitude: float = 500.0
    tz: str = "Asia/Kolkata"


class PanelSpec(BaseModel):
    """Small 6.9 V PV module of the physical rig."""

    voc_stc: float = 6.9  # open-circuit voltage at 1000 W/m2, 25 C
    isc_stc: float = 1.5  # short-circuit current at STC (A)
    beta_voc: float = -0.0033  # 1/K
    alpha_isc: float = 0.0005  # 1/K
    low_light_k: float = 0.06  # Voc ~ (1 + k ln(G/1000))
    noct: float = 45.0  # nominal operating cell temperature (C)


class Weather(BaseModel):
    cloud_model: Literal["clear", "markov"] = "markov"
    mean_cloud_cover: float = Field(0.2, ge=0, le=1)
    cloud_persistence_s: float = 600.0
    ambient_min_c: float = 24.0
    ambient_max_c: float = 36.0
    irradiance_override: float | None = None  # W/m2; fixed "lab lamp" mode when set


class Fault(BaseModel):
    """A time-windowed fault. `target` is A/B/C/D for the rig, P1..PN for farm mode, or all."""

    kind: Literal[
        "disconnect",  # panel produces nothing
        "shading",  # value = fraction of irradiance blocked (0..1)
        "degradation",  # value = fractional Voc/Isc loss (0..1)
        "sensor_stuck",  # value = raw ADC code reported
        "sensor_noise",  # value = sigma in V (A for D)
        "adc_saturation",  # raw pinned to 4095
    ]
    target: str = "all"
    start_s: float = 0.0
    end_s: float | None = None
    value: float = 0.0

    def active(self, t_s: float) -> bool:
        return self.start_s <= t_s and (self.end_s is None or t_s < self.end_s)

    def hits(self, target: str) -> bool:
        return self.target in ("all", target)


class Network(BaseModel):
    """Transport-level behaviour of the emulated ESP32 HTTP endpoint."""

    mode: Literal["ok", "latency", "hang", "http_500", "malformed_json", "missing_keys", "down"] = (
        "ok"
    )
    latency_ms: float = 0.0
    hang_s: float = 30.0
    # None = faithful to the firmware backend; True/False force the CORS header on/off.
    cors: bool | None = None


class Farm(BaseModel):
    """Utility-scale plant used for the Kaggle-schema datasets and /api/v2 farm mode."""

    plant_id: int = 4136001
    inverters: int = 22
    dc_kw_per_inverter: float = 1400.0
    capacity_spread: float = 0.05
    inverter_efficiency: float = 0.975
    efficiency_noise: float = 0.002
    temp_coeff: float = -0.004  # 1/K power loss
    outage_rate: float = 0.002  # probability a 15-min slot of one inverter is offline
    n_panels: int = 8  # panels exposed by /api/v2


class Scenario(BaseModel):
    name: str = "default"
    description: str = ""
    seed: int = 42
    start: datetime = datetime(2020, 5, 15, 6, 0)
    duration_s: float = 12 * 3600.0
    tick_s: float = 2.0  # firmware BlynkTimer interval
    site: Site = Site()
    panel: PanelSpec = PanelSpec()
    weather: Weather = Weather()
    faults: list[Fault] = []
    network: Network = Network()
    adc_model: Literal["ideal", "esp32"] = "ideal"  # ideal = firmware's assumed transfer
    acs_divider: bool = True  # esp32 model only: ACS712 output divided 5V->3.3V before GPIO33
    adc_noise_lsb: float = 0.0
    load_ohm: float = 8.0  # resistive load on the C+D series string
    blynk_token: str = "sim-token"
    farm: Farm = Farm()

    @classmethod
    def load(cls, path: str | Path) -> Scenario:
        p = Path(path)
        if not p.exists() and not p.is_absolute():
            p = SCENARIO_DIR / p
            if p.suffix == "":
                p = p.with_suffix(".yaml")
        return cls.model_validate(yaml.safe_load(p.read_text()) or {})

    def dump(self) -> str:
        return yaml.safe_dump(self.model_dump(mode="json"), sort_keys=False)
