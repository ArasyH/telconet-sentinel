"""Tests for citation check and judge logic. [REQ-3.8–3.12]"""

import json

from telconet_sentinel.agents.judge import citation_check, judge_draft
from telconet_sentinel.agents.llm_client import reset_fake_llm
from telconet_sentinel.schemas import GeneratorOutput, Verdict


def _make_draft(sop_id="SOP-FTTH-001", step=1, iteration=1) -> GeneratorOutput:
    return GeneratorOutput.model_validate({
        "incident_id": "INC-TEST-001",
        "device_id": "ONT-BDG-001",
        "predicted_status": "Warning",
        "root_cause_hypothesis": "Fiber degradation",
        "root_cause_category": "FIBER_DEGRADATION",
        "telemetry_evidence": [
            {"metric": "rx_optical_power_dbm", "observed_value": -26.0,
             "threshold": -25.0, "interpretation": "Warning"}
        ],
        "action_plan": [
            {"step_no": 1, "action": "Check rx power",
             "sop_reference": {"sop_id": sop_id, "step": step}, "priority": "P1"}
        ],
        "confidence": 0.75,
        "status_flag": "OK",
        "iteration": iteration,
    })


def _fake_chunks_with(sop_id: str, step: int) -> list[dict]:
    return [{
        "text": f"[{sop_id}] Tindakan — Step {step}",
        "metadata": {"sop_id": sop_id, "domain": "FTTH", "section": "Tindakan",
                     "source_file": f"{sop_id}.md", "step": f"Step {step}"},
        "distance": 0.1,
    }]


def _fake_ctx(device_id="ONT-BDG-001") -> dict:
    return {
        "device_id": device_id,
        "device_type": "ONT",
        "region": "BANDUNG",
        "predicted_status": "Warning",
        "ml_probabilities": {"Normal": 0.1, "Warning": 0.8, "Critical": 0.1},
        "telemetry_last_12": [],
        "sop_chunks": _fake_chunks_with("SOP-FTTH-001", 1),
    }


# ── citation_check tests ─────────────────────────────────────────────────────

def test_valid_citation_no_invalid():
    draft = _make_draft("SOP-FTTH-001", 1)
    chunks = _fake_chunks_with("SOP-FTTH-001", 1)
    result = citation_check(draft, chunks)
    assert result == []


def test_invalid_citation_detected():
    draft = _make_draft("SOP-FTTH-001", 7)  # step 7 not in chunks
    chunks = _fake_chunks_with("SOP-FTTH-001", 1)
    result = citation_check(draft, chunks)
    assert len(result) == 1
    assert result[0].step == 7


# ── judge_draft verdict enforcement ─────────────────────────────────────────

def test_score_95_valid_citations_approved():
    """Score 95 + no invalid citations → APPROVED."""
    judge_response = json.dumps({
        "incident_id": "INC-TEST-001",
        "iteration": 1,
        "sop_faithfulness_score": 95,
        "telemetry_consistency_score": 90,
        "verdict": "APPROVED",
        "issues": [],
        "invalid_citations": [],
        "revision_instructions": "",
        "rationale": "All good.",
    })
    reset_fake_llm(["PLACEHOLDER_GEN", judge_response])
    # Consume placeholder for generator slot
    from telconet_sentinel.agents.llm_client import get_llm
    llm = get_llm()
    llm.complete_json("", "", 0.0)  # consume placeholder

    draft = _make_draft("SOP-FTTH-001", 1)
    ctx = _fake_ctx()
    chunks = _fake_chunks_with("SOP-FTTH-001", 1)
    result = judge_draft(draft, ctx, chunks)
    assert result.verdict == Verdict.APPROVED


def test_score_79_forced_revision():
    """Score 79 (below threshold 80) → REVISION_NEEDED regardless of LLM verdict."""
    judge_response = json.dumps({
        "incident_id": "INC-TEST-001",
        "iteration": 1,
        "sop_faithfulness_score": 79,
        "telemetry_consistency_score": 80,
        "verdict": "APPROVED",  # LLM tries to approve but rule overrides
        "issues": [],
        "invalid_citations": [],
        "revision_instructions": "",
        "rationale": "Slight gap.",
    })
    reset_fake_llm([judge_response])
    draft = _make_draft("SOP-FTTH-001", 1)
    ctx = _fake_ctx()
    chunks = _fake_chunks_with("SOP-FTTH-001", 1)
    result = judge_draft(draft, ctx, chunks)
    assert result.verdict == Verdict.REVISION_NEEDED


def test_score_95_invalid_citation_forced_revision():
    """Score 95 but invalid citation → REVISION_NEEDED (REQ-3.11)."""
    judge_response = json.dumps({
        "incident_id": "INC-TEST-001",
        "iteration": 1,
        "sop_faithfulness_score": 95,
        "telemetry_consistency_score": 90,
        "verdict": "APPROVED",
        "issues": [],
        "invalid_citations": [],
        "revision_instructions": "",
        "rationale": "Good.",
    })
    reset_fake_llm([judge_response])
    draft = _make_draft("SOP-FTTH-001", 7)  # step 7 NOT in chunks
    ctx = _fake_ctx()
    chunks = _fake_chunks_with("SOP-FTTH-001", 1)
    result = judge_draft(draft, ctx, chunks)
    assert result.verdict == Verdict.REVISION_NEEDED
    assert len(result.invalid_citations) > 0


def test_score_80_no_invalid_approved():
    """Score exactly 80 + no invalid citations → APPROVED (REQ-3.12)."""
    judge_response = json.dumps({
        "incident_id": "INC-TEST-001",
        "iteration": 1,
        "sop_faithfulness_score": 80,
        "telemetry_consistency_score": 85,
        "verdict": "APPROVED",
        "issues": [],
        "invalid_citations": [],
        "revision_instructions": "",
        "rationale": "Meets threshold.",
    })
    reset_fake_llm([judge_response])
    draft = _make_draft("SOP-FTTH-001", 1)
    ctx = _fake_ctx()
    chunks = _fake_chunks_with("SOP-FTTH-001", 1)
    result = judge_draft(draft, ctx, chunks)
    assert result.verdict == Verdict.APPROVED
