"""Tests for orchestrator loop. [REQ-3.13–3.16, 3.18]

Uses monkeypatching to inject controlled contexts so tests are independent
of ChromaDB, CSV, and ML model state.
"""

import json

import pytest

from telconet_sentinel.agents.llm_client import (
    _FAKE_GENERATOR_RESPONSE,
    _FAKE_JUDGE_APPROVED,
    _FAKE_JUDGE_REVISION,
    reset_fake_llm,
)
from telconet_sentinel.agents.orchestrator import run_rca
from telconet_sentinel.schemas import FinalStatus


def _fake_ctx(device_id: str = "ONT-BDG-001") -> dict:
    """Controlled context with a step chunk so citations can pass."""
    return {
        "device_id": device_id,
        "device_type": "ONT",
        "region": "BANDUNG",
        "predicted_status": "Warning",
        "ml_probabilities": {"Normal": 0.1, "Warning": 0.8, "Critical": 0.1},
        "telemetry_last_12": [],
        "sop_chunks": [
            {
                "text": "[SOP-FTTH-001] Tindakan — Step 1\nStep 1: Verifikasi rx power dari NMS.",
                "metadata": {
                    "sop_id": "SOP-FTTH-001", "domain": "FTTH",
                    "section": "Tindakan", "source_file": "SOP-FTTH-001.md", "step": "Step 1",
                },
                "distance": 0.05,
            }
        ],
    }


@pytest.fixture(autouse=True)
def patch_context(monkeypatch):
    """Inject controlled context so orchestrator doesn't need real CSV/Chroma."""
    monkeypatch.setattr(
        "telconet_sentinel.agents.orchestrator.build_incident_context",
        lambda device_id, **kwargs: _fake_ctx(device_id),
    )


def test_approve_iteration_1():
    reset_fake_llm([_FAKE_GENERATOR_RESPONSE, _FAKE_JUDGE_APPROVED])
    result = run_rca("ONT-BDG-001")
    assert result.final_status == FinalStatus.APPROVED
    assert len(result.iterations) == 1


def test_revision_then_approve():
    judge_approved_iter2 = json.loads(_FAKE_JUDGE_APPROVED)
    judge_approved_iter2["iteration"] = 2
    reset_fake_llm([
        _FAKE_GENERATOR_RESPONSE,
        _FAKE_JUDGE_REVISION,
        _FAKE_GENERATOR_RESPONSE,
        json.dumps(judge_approved_iter2),
    ])
    result = run_rca("ONT-BDG-001")
    assert result.final_status == FinalStatus.APPROVED
    assert len(result.iterations) == 2


def test_two_revisions_escalate():
    revision2 = json.loads(_FAKE_JUDGE_REVISION)
    revision2["iteration"] = 2
    reset_fake_llm([
        _FAKE_GENERATOR_RESPONSE, _FAKE_JUDGE_REVISION,
        _FAKE_GENERATOR_RESPONSE, json.dumps(revision2),
    ])
    result = run_rca("ONT-BDG-001")
    assert result.final_status == FinalStatus.UNVERIFIED_ESCALATE_TO_HUMAN
    assert len(result.iterations) == 2


def test_broken_json_twice_returns_error():
    reset_fake_llm(["not json at all", "still not json"])
    result = run_rca("ONT-BDG-001")
    assert result.final_status == FinalStatus.ERROR


def test_empty_sop_chunks_returns_error(monkeypatch):
    """Orchestrator returns ERROR when no SOP chunks retrieved."""
    monkeypatch.setattr(
        "telconet_sentinel.agents.orchestrator.build_incident_context",
        lambda device_id, **kwargs: {**_fake_ctx(device_id), "sop_chunks": []},
    )
    reset_fake_llm([_FAKE_GENERATOR_RESPONSE, _FAKE_JUDGE_APPROVED])
    result = run_rca("ONT-BDG-001")
    assert result.final_status == FinalStatus.ERROR
