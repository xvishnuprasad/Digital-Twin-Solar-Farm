"""F6: credentials must not be committed in the sketch."""

import re

import pytest

from sim.conftest_helpers import REPO


@pytest.mark.covers("FEAT-MON")
def test_sketch_has_no_inline_credentials():
    src = (REPO / "Solar_Farm.ino").read_text()
    assert '#include "secrets.h"' in src
    assert not re.search(r'char\s+(ssid|pass)\[\]\s*=\s*"', src), "Wi-Fi credentials hard-coded"
    assert not re.search(r'#define\s+BLYNK_AUTH_TOKEN\s+"', src), "Blynk token hard-coded"


@pytest.mark.covers("FEAT-MON")
def test_secrets_template_present_and_real_file_ignored():
    assert (REPO / "secrets.example.h").exists()
    assert "secrets.h" in (REPO / ".gitignore").read_text().split()
