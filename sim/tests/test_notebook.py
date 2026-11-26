"""ML notebook (Untitled3.ipynb) executed against generated Kaggle-schema data (criterion 6)."""

import os
import re

import nbformat
import pytest
from nbclient import NotebookClient

from sim.conftest_helpers import NOTEBOOK
from sim.datasets import WEATHER_FILE, generate_kaggle

DRIVE_DIR = "/content/drive/MyDrive/ML/CSV Files"


def code(nb) -> str:
    return "\n".join(c.source for c in nb.cells if c.cell_type == "code")


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("nbdata")
    truth = generate_kaggle(d, days=6, inverters=4, seed=11)
    return d, truth


@pytest.mark.covers("FEAT-ML")
def test_notebook_reads_weather_csv():
    assert WEATHER_FILE in code(nbformat.read(NOTEBOOK, as_version=4))


@pytest.mark.covers("FEAT-ML")
def test_notebook_r2_argument_order():
    src = code(nbformat.read(NOTEBOOK, as_version=4))
    assert "r2_score(y_pred" not in src and re.search(r"r2_score\(\s*y_test", src)


@pytest.mark.covers("FEAT-ML", "HARN-DATA")
def test_notebook_runs_and_recovers_inverter_efficiency(data_dir, tmp_path):
    d, truth = data_dir
    nb = nbformat.read(NOTEBOOK, as_version=4)
    for c in nb.cells:  # only the data location is edited
        c.source = c.source.replace(DRIVE_DIR, str(d))
    os.environ["SOLAR_DATA_DIR"] = str(d)
    os.environ.setdefault("MPLBACKEND", "Agg")
    NotebookClient(
        nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(tmp_path)}}
    ).execute()
    text = "\n".join(
        o.get("text", "")
        for c in nb.cells
        if c.cell_type == "code"
        for o in c.get("outputs", [])
        if o.get("name") == "stdout"
    )
    eff = float(re.search(r"Efficiency\) of Solar Power Plant:\s+([\d.]+) %", text).group(1))
    assert eff == pytest.approx(truth["inverter_efficiency"] * 100, abs=1.0)
    # F10: unscaled ~1e9 TOTAL_YIELD features made LinearRegression collapse (R2 ~ 0)
    r2 = float(re.search(r"R2 Score :\s+(-?[\d.]+) %", text).group(1))
    assert r2 > 95
