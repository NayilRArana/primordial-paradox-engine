"""Shared fixtures: the tools directory on the import path, and a throwaway copy of data\\ to break on purpose."""

from __future__ import annotations

import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)


@pytest.fixture()
def data_root(tmp_path):
    """A private root with a copy of data\\ inside, so a test can corrupt one file and nothing else."""
    shutil.copytree(os.path.join(ROOT, "data"), tmp_path / "data")
    return tmp_path


@pytest.fixture()
def read_json():
    def _read(path):
        import json
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    return _read


@pytest.fixture()
def write_json():
    def _write(path, data):
        import json
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")

    return _write
