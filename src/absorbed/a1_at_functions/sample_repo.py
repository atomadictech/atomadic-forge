"""Shared fixtures for the Atomadic Forge test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make ``src/`` importable without an editable install (CI shortcut).
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def sample_repo(tmp_path: Path) -> Path:
    """Tiny mixed pure/stateful Python repo used across tests."""
    (tmp_path / "pure.py").write_text(
        '"""Pure helpers."""\n\n'
        "def add(a, b):\n    return a + b\n\n"
        "def divide(a, b):\n    if b == 0:\n        raise ValueError('zero')\n"
        "    return a / b\n\n"
        "class Counter:\n    def __init__(self):\n        self.n = 0\n"
        "    def incr(self):\n        self.n += 1\n        return self.n\n",
        encoding="utf-8",
    )
    (tmp_path / "io_runner.py").write_text(
        '"""I/O orchestrator."""\n\n'
        "import urllib.request\n\n"
        "def fetch(url):\n    return urllib.request.urlopen(url).read()\n\n"
        "def main():\n    print('starting')\n    print('done')\n",
        encoding="utf-8",
    )
    return tmp_path
