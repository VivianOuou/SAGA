import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scileo_agent.utils.logging import setup_logging  # noqa: E402

setup_logging(level="WARNING")


@pytest.fixture
def repo_root():
    return ROOT


@pytest.fixture
def fresh_registry():
    from scileo_agent.core.registry.scorer_registry import reset_scorer_manager

    reset_scorer_manager()
    yield
    reset_scorer_manager()


@pytest.fixture
def in_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path
