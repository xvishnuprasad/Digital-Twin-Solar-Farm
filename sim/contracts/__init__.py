"""JSON Schemas for the telemetry contracts + validation helpers."""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

import jsonschema

HERE = Path(__file__).parent
TWO_DECIMALS = re.compile(r'"Panel[A-D]_(?:Voltage|Current)":(-?\d+\.\d{2})(?=[,}])')


@cache
def schema(version: str = "v1") -> dict:
    return json.loads((HERE / f"api_{version}.schema.json").read_text())


def validate(payload: dict, version: str = "v1") -> None:
    jsonschema.validate(payload, schema(version))


def errors(payload: dict, version: str = "v1") -> list[str]:
    v = jsonschema.Draft202012Validator(schema(version))
    return [e.message for e in v.iter_errors(payload)]


def check_v1_body(body: str) -> list[str]:
    """Validate a raw /api body: JSON schema + exactly two decimals per number."""
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]
    errs = errors(data, "v1")
    if len(TWO_DECIMALS.findall(body)) != 4:
        errs.append("numeric fields must be formatted with exactly two decimals")
    return errs
