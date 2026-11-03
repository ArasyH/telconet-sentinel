"""Citation check (deterministic) + Judge Agent. [REQ-3.8–3.12]"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from telconet_sentinel.agents.context import format_context_for_prompt
from telconet_sentinel.agents.llm_client import get_llm
from telconet_sentinel.agents.prompts import JUDGE_SYSTEM
from telconet_sentinel.config import settings
from telconet_sentinel.schemas import (
    GeneratorOutput,
    InvalidCitation,
    JudgeOutput,
)


def _parse_step_number(step_str: str) -> int | None:
    """Parse 'Step N' → N."""
    import re
    m = re.search(r"\d+", step_str)
    return int(m.group()) if m else None


def citation_check(draft: GeneratorOutput, chunks: list[dict]) -> list[InvalidCitation]:
    """Non-LLM check: every cited sop_id+step must exist in retrieved chunks. [REQ-3.10]"""
    # Build set of (sop_id, step_number) present in chunks
    available: set[tuple[str, int]] = set()
    for chunk in chunks:
        sop_id = chunk["metadata"].get("sop_id", "")
        step_str = chunk["metadata"].get("step", "")
        step_num = _parse_step_number(step_str) if step_str else None
        if step_num is not None:
            available.add((sop_id, step_num))

    invalid: list[InvalidCitation] = []
    for action in draft.action_plan:
        ref = action.sop_reference
        if (ref.sop_id, ref.step) not in available:
            invalid.append(InvalidCitation(sop_id=ref.sop_id, step=ref.step))
    return invalid


def judge_draft(
    draft: GeneratorOutput,
    context: dict[str, Any],
    chunks: list[dict],
) -> JudgeOutput:
    """Score the draft with the Judge LLM, then enforce deterministic verdict rules."""
    invalid_citations = citation_check(draft, chunks)

    llm = get_llm()
    context_text = format_context_for_prompt(context)
    draft_json = draft.model_dump_json(indent=2)

    citation_result = (
        "No invalid citations found."
        if not invalid_citations
        else "INVALID CITATIONS (confirmed by system): "
             + ", ".join(f"{c.sop_id} Step {c.step}" for c in invalid_citations)
    )

    user_msg = (
        f"<DRAFT_RCA>\n{draft_json}\n</DRAFT_RCA>\n\n"
        f"{context_text}\n\n"
        f"<CITATION_CHECK_RESULT>\n{citation_result}\n</CITATION_CHECK_RESULT>"
    )

    raw = ""
    for attempt in range(2):
        try:
            raw = llm.complete_json(JUDGE_SYSTEM, user_msg, settings.judge_temperature)
            output = JudgeOutput.model_validate_json(raw)
            break
        except (ValidationError, json.JSONDecodeError, Exception) as exc:
            if attempt == 0:
                user_msg = (
                    f"Your previous response was invalid. Error: {exc}\n"
                    f"Previous response: {raw}\n"
                    f"Respond with valid JSON only."
                )
            else:
                raise
    else:
        raise RuntimeError("judge_draft: exhausted retries")

    # Enforce invalid citations → REVISION_NEEDED (REQ-3.11)
    data = output.model_dump()
    data["invalid_citations"] = [c.model_dump() for c in invalid_citations]
    if invalid_citations and data["verdict"] == "APPROVED":
        data["verdict"] = "REVISION_NEEDED"
        if not data.get("revision_instructions"):
            sop_list = ", ".join(f"{c.sop_id} Step {c.step}" for c in invalid_citations)
            data["revision_instructions"] = (
                f"Remove or fix invalid citations: {sop_list}. "
                f"Only cite steps that appear in the provided SOP context."
            )

    # Enforce score < threshold → REVISION_NEEDED (REQ-3.12)
    if data["sop_faithfulness_score"] < settings.approval_threshold and data["verdict"] == "APPROVED":
        data["verdict"] = "REVISION_NEEDED"
        if not data.get("revision_instructions"):
            data["revision_instructions"] = (
                f"SOP faithfulness score {data['sop_faithfulness_score']} is below "
                f"threshold {settings.approval_threshold}. Improve SOP adherence."
            )

    # Stamp correct incident_id and iteration
    data["incident_id"] = draft.incident_id
    data["iteration"] = draft.iteration

    return JudgeOutput.model_validate(data)
