"""Environment + PV physics: irradiance, clouds, temperature, panel V/I, faults."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pvlib

from .config import PanelSpec, Scenario

GRID_S = 60.0  # resolution of the precomputed environment grid
RIG_PANELS = ("A", "B", "C", "D")


def clearsky_ghi(times: pd.DatetimeIndex, sc: Scenario) -> np.ndarray:
    """Clear-sky global horizontal irradiance (W/m2), Haurwitz model (no extra data files)."""
    loc = pvlib.location.Location(
        sc.site.latitude, sc.site.longitude, tz=sc.site.tz, altitude=sc.site.altitude
    )
    ghi = loc.get_clearsky(times, model="haurwitz")["ghi"].to_numpy()
    return np.clip(np.nan_to_num(ghi), 0.0, None)


def cloud_index(n: int, step_s: float, sc: Scenario) -> np.ndarray:
    """Seeded Markov clear-sky index kt in (0, 1]: clear or cloudy segments, smoothed."""
    if sc.weather.cloud_model == "clear":
        return np.ones(n)
    rng = np.random.default_rng([sc.seed, 7])
    seg = max(1, round(sc.weather.cloud_persistence_s / step_s))
    n_seg = n // seg + 2
    cloudy = rng.random(n_seg) < sc.weather.mean_cloud_cover
    level = np.where(cloudy, rng.uniform(0.2, 0.6, n_seg), rng.uniform(0.95, 1.0, n_seg))
    x = np.arange(n) / seg
    return np.interp(x, np.arange(n_seg), level)


def ambient_temp(times: pd.DatetimeIndex, sc: Scenario) -> np.ndarray:
    """Diurnal sinusoid: minimum ~06:00, maximum ~15:00 local time."""
    hours = times.hour + times.minute / 60.0 + times.second / 3600.0
    lo, hi = sc.weather.ambient_min_c, sc.weather.ambient_max_c
    return (lo + hi) / 2 + (hi - lo) / 2 * np.sin(2 * np.pi * (np.asarray(hours) - 9.0) / 24.0)


def module_temp(ambient: np.ndarray | float, ghi: np.ndarray | float, noct: float):
    return ambient + np.asarray(ghi) * (noct - 20.0) / 800.0


def panel_voc(g: float, t_cell: float, spec: PanelSpec, degradation: float = 0.0) -> float:
    """Open-circuit-ish terminal voltage (dividers draw ~no current)."""
    if g < 1.0:
        return 0.0
    v = (
        spec.voc_stc
        * (1 + spec.beta_voc * (t_cell - 25.0))
        * (1 + spec.low_light_k * np.log(g / 1000.0))
    )
    return max(0.0, float(v) * (1.0 - degradation))


def panel_isc(g: float, t_cell: float, spec: PanelSpec, degradation: float = 0.0) -> float:
    return max(
        0.0, spec.isc_stc * g / 1000.0 * (1 + spec.alpha_isc * (t_cell - 25.0)) * (1 - degradation)
    )


@dataclass
class PanelState:
    g_eff: float
    voltage: float
    isc: float
    connected: bool


class Environment:
    """Precomputed (seeded, deterministic) environment over the scenario window."""

    def __init__(self, sc: Scenario):
        self.sc = sc
        n = int((sc.duration_s + 3600) // GRID_S) + 2
        self.times = pd.date_range(sc.start, periods=n, freq=f"{int(GRID_S)}s", tz=sc.site.tz)
        self.t_grid = np.arange(n) * GRID_S
        self.ghi_clear = clearsky_ghi(self.times, sc)
        self.kt = cloud_index(n, GRID_S, sc)
        self.t_amb = ambient_temp(self.times, sc)

    def irradiance(self, t_s: float) -> float:
        ov = self.sc.weather.irradiance_override
        if ov is not None:
            return float(ov)
        return float(np.interp(t_s, self.t_grid, self.ghi_clear * self.kt))

    def ambient(self, t_s: float) -> float:
        w = self.sc.weather
        if w.ambient_min_c == w.ambient_max_c:
            return w.ambient_min_c
        return float(np.interp(t_s, self.t_grid, self.t_amb))

    def panel(self, name: str, t_s: float) -> PanelState:
        g = self.irradiance(t_s)
        t_cell = float(module_temp(self.ambient(t_s), g, self.sc.panel.noct))
        shade, degr, connected = 0.0, 0.0, True
        for f in self.sc.faults:
            if not (f.active(t_s) and f.hits(name)):
                continue
            if f.kind == "disconnect":
                connected = False
            elif f.kind == "shading":
                shade = max(shade, min(1.0, f.value))
            elif f.kind == "degradation":
                degr = max(degr, min(1.0, f.value))
        g_eff = g * (1 - shade) if connected else 0.0
        return PanelState(
            g_eff=g_eff,
            voltage=panel_voc(g_eff, t_cell, self.sc.panel, degr) if connected else 0.0,
            isc=panel_isc(g_eff, t_cell, self.sc.panel, degr) if connected else 0.0,
            connected=connected,
        )

    def rig_truth(self, t_s: float) -> dict:
        """Physical ground truth of the 4-panel rig at time t."""
        p = {n: self.panel(n, t_s) for n in RIG_PANELS}
        g = self.irradiance(t_s)
        # Series string C+D into a resistive load: weakest panel limits the current.
        v_string = p["C"].voltage + p["D"].voltage
        i_d = min(p["C"].isc, p["D"].isc, v_string / self.sc.load_ohm) if v_string > 0 else 0.0
        return {
            "t_s": t_s,
            "irradiance_wm2": g,
            "ambient_c": self.ambient(t_s),
            "module_c": float(module_temp(self.ambient(t_s), g, self.sc.panel.noct)),
            "V_A": p["A"].voltage,
            "V_B": p["B"].voltage,
            "V_C": p["C"].voltage,
            "V_D": p["D"].voltage,
            "I_D": float(i_d),
        }
