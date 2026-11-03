"""Generator Agent — produces RCA draft. [REQ-3.6, 3.7, 3.13, 3.17]"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from telconet_sentinel.agents.context import format_context_for_prompt
from telconet_sentinel.agents.llm_client import get_llm
from telconet_sentinel.agents.prompts import (
    GENERATOR_REVISION_ADDENDUM,
    GENERATOR_SYSTEM,
)
from telconet_sentinel.config import settings
from telconet_sentinel.schemas import GeneratorOutput


def generate_draft(
    context: dict[str, Any],
    iteration: int,
    feedback: str | None = None,
) -> GeneratorOutput:
    """Call LLM to produce a GeneratorOutput; retries once on JSON/schema error."""
    llm = get_llm()
    context_text = format_context_for_prompt(context)

    system = GENERATOR_SYSTEM
    if feedback:
        system += GENERATOR_REVISION_ADDENDUM.format(feedback=feedback)

    user_msg = (
        f"Generate an RCA for the incident above. iteration={iteration}.\n\n"
        f"{context_text}"
    )

    raw = ""
    for attempt in range(2):
        try:
            raw = llm.complete_json(system, user_msg, settings.generator_temperature)
            output = GeneratorOutput.model_validate_json(raw)
            # Stamp correct device_id and iteration regardless of LLM output
            return output.model_copy(update={
                "device_id": context["device_id"],
                "iteration": iteration,
            })
        except (ValidationError, json.JSONDecodeError, Exception) as exc:
            if attempt == 0:
                # Second attempt: ask LLM to fix its JSON
                user_msg = (
                    f"Your previous response was not valid JSON conforming to the schema. "
                    f"Error: {exc}\n"
                    f"Previous response: {raw}\n"
                    f"Please respond with valid JSON only."
                )
            else:
                raise
    raise RuntimeError("generate_draft: exhausted retries")
