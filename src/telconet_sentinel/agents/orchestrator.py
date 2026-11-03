"""RCA orchestrator loop — max 2 iterations. [REQ-3.13–3.16, 3.18]"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from telconet_sentinel.agents.context import build_incident_context
from telconet_sentinel.agents.generator import generate_draft
from telconet_sentinel.agents.judge import judge_draft
from telconet_sentinel.agents.llm_client import get_llm
from telconet_sentinel.config import settings
from telconet_sentinel.schemas import (
    FinalStatus,
    IterationRecord,
    RcaResult,
    Verdict,
)


def _make_incident_id(device_id: str) -> str:
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M")
    return f"INC-{device_id}-{ts}"


def run_rca(
    device_id: str,
    csv_path: str | None = None,
    chroma_dir: str | None = None,
) -> RcaResult:
    """Run Generator→Judge loop for device_id; return RcaResult. [REQ-3.13–3.16]"""
    incident_id = _make_incident_id(device_id)
    total_start = time.monotonic()

    # Build context
    try:
        context = build_incident_context(device_id, csv_path=csv_path, chroma_dir=chroma_dir)
    except Exception as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            msg += " — is ChromaDB populated? Run rag.ingest first."
        return RcaResult(
            incident_id=incident_id,
            final_status=FinalStatus.ERROR,
            error=msg,
            total_latency_ms=_ms_since(total_start),
            model=get_llm().model,
        )

    sop_chunks = context.get("sop_chunks", [])
    retrieved_sop_ids = list({c["metadata"]["sop_id"] for c in sop_chunks})

    if not sop_chunks:
        return RcaResult(
            incident_id=incident_id,
            final_status=FinalStatus.ERROR,
            error="No SOP chunks retrieved — run rag.ingest first.",
            retrieved_sop_ids=[],
            total_latency_ms=_ms_since(total_start),
            model=get_llm().model,
        )

    iterations: list[IterationRecord] = []
    revision_instructions: str | None = None

    for iteration in range(1, settings.max_iterations + 1):
        iter_start = time.monotonic()

        # Generator
        try:
            draft = generate_draft(
                context, iteration=iteration, feedback=revision_instructions
            )
            # stamp incident_id
            data = draft.model_dump()
            data["incident_id"] = incident_id
            from telconet_sentinel.schemas import GeneratorOutput
            draft = GeneratorOutput.model_validate(data)
        except Exception as exc:
            record_partial = IterationRecord(
                draft=_error_draft(incident_id, device_id, iteration),
                judge=_error_judge(incident_id, iteration, str(exc)),
                latency_ms=_ms_since(iter_start),
            )
            iterations.append(record_partial)
            _log_result(RcaResult(
                incident_id=incident_id,
                final_status=FinalStatus.ERROR,
                iterations=iterations,
                retrieved_sop_ids=retrieved_sop_ids,
                total_latency_ms=_ms_since(total_start),
                model=get_llm().model,
                error=str(exc),
            ))
            return RcaResult(
                incident_id=incident_id,
                final_status=FinalStatus.ERROR,
                iterations=iterations,
                retrieved_sop_ids=retrieved_sop_ids,
                total_latency_ms=_ms_since(total_start),
                model=get_llm().model,
                error=str(exc),
            )

        # Judge
        try:
            judge_out = judge_draft(draft, context, sop_chunks)
        except Exception as exc:
            record_partial = IterationRecord(
                draft=draft,
                judge=_error_judge(incident_id, iteration, str(exc)),
                latency_ms=_ms_since(iter_start),
            )
            iterations.append(record_partial)
            result = RcaResult(
                incident_id=incident_id,
                final_status=FinalStatus.ERROR,
                iterations=iterations,
                retrieved_sop_ids=retrieved_sop_ids,
                total_latency_ms=_ms_since(total_start),
                model=get_llm().model,
                error=str(exc),
            )
            _log_result(result)
            return result

        iterations.append(IterationRecord(
            draft=draft,
            judge=judge_out,
            latency_ms=_ms_since(iter_start),
        ))

        if judge_out.verdict == Verdict.APPROVED:
            result = RcaResult(
                incident_id=incident_id,
                final_status=FinalStatus.APPROVED,
                final_draft=draft,
                iterations=iterations,
                retrieved_sop_ids=retrieved_sop_ids,
                total_latency_ms=_ms_since(total_start),
                model=get_llm().model,
            )
            _log_result(result)
            return result

        revision_instructions = judge_out.revision_instructions or "Revise per judge feedback."

    # After max iterations still REVISION_NEEDED → escalate
    result = RcaResult(
        incident_id=incident_id,
        final_status=FinalStatus.UNVERIFIED_ESCALATE_TO_HUMAN,
        final_draft=iterations[-1].draft if iterations else None,
        iterations=iterations,
        retrieved_sop_ids=retrieved_sop_ids,
        total_latency_ms=_ms_since(total_start),
        model=get_llm().model,
    )
    _log_result(result)
    return result


def _ms_since(start: float) -> float:
    return (time.monotonic() - start) * 1000


def _error_draft(incident_id: str, device_id: str, iteration: int):
    from telconet_sentinel.schemas import GeneratorOutput
    return GeneratorOutput.model_validate({
        "incident_id": incident_id,
        "device_id": device_id,
        "predicted_status": "Warning",
        "root_cause_hypothesis": "Error during generation.",
        "root_cause_category": "UNKNOWN",
        "telemetry_evidence": [],
        "action_plan": [{
            "step_no": 1, "action": "Escalate to human operator",
            "sop_reference": {"sop_id": "SOP-FTTH-001", "step": 1}, "priority": "P1"
        }],
        "confidence": 0.0,
        "status_flag": "INSUFFICIENT_SOP_CONTEXT",
        "iteration": iteration,
    })


def _error_judge(incident_id: str, iteration: int, error_msg: str):
    from telconet_sentinel.schemas import JudgeOutput
    short_msg = error_msg[:300]
    return JudgeOutput.model_validate({
        "incident_id": incident_id,
        "iteration": iteration,
        "sop_faithfulness_score": 1,
        "telemetry_consistency_score": 1,
        "verdict": "REVISION_NEEDED",
        "issues": [],
        "invalid_citations": [],
        "revision_instructions": f"Error: {short_msg}",
        "rationale": f"System error: {short_msg[:200]}",
    })


def _log_result(result: RcaResult) -> None:
    """Append result to JSONL log file. [REQ-3.16]"""
    try:
        settings.logs_dir.mkdir(parents=True, exist_ok=True)
        entry = result.model_dump()
        entry["logged_at"] = datetime.now(tz=timezone.utc).isoformat()
        with open(settings.rca_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass  # logging must not crash the main flow
