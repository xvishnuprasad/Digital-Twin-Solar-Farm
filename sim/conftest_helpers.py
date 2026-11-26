"""Paths shared by tests (kept outside conftest so test modules can import them)."""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO / "index.html"
NOTEBOOK = REPO / "Untitled3.ipynb"
