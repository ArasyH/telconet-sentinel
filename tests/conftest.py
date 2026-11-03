"""Shared pytest fixtures. Sets LLM_MODE=fake and redirects DATA_DIR to tmp_path."""

import os

import pytest


def pytest_configure(config):
    os.environ["LLM_MODE"] = "fake"


@pytest.fixture(autouse=True)
def fake_llm_env(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "fake")


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirect settings.data_dir to a temp dir and create sub-folders."""
    for sub in ("raw", "sop", "chroma", "artifacts", "logs"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # Re-import settings with patched env
    import importlib

    import telconet_sentinel.config as cfg_mod
    importlib.reload(cfg_mod)
    return tmp_path
