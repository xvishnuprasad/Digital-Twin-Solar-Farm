"""The sketch still compiles for the real ESP32 target (arduino-cli; slow, opt-in)."""

import shutil
import subprocess

import pytest

from sim.conftest_helpers import REPO


@pytest.mark.slow
@pytest.mark.covers("FEAT-MON")
def test_sketch_compiles_for_esp32(tmp_path):
    if not shutil.which("arduino-cli"):
        pytest.skip("arduino-cli not installed")
    sketch = tmp_path / "Solar_Farm"
    sketch.mkdir()
    shutil.copy(REPO / "Solar_Farm.ino", sketch)
    example = REPO / "secrets.example.h"
    if example.exists():
        shutil.copy(example, sketch / "secrets.h")
    res = subprocess.run(
        ["arduino-cli", "compile", "-b", "esp32:esp32:esp32", str(sketch)],
        capture_output=True, text=True, timeout=900, check=False,
    )  # fmt: skip
    assert res.returncode == 0, res.stderr[-3000:]
    assert "Sketch uses" in res.stdout
