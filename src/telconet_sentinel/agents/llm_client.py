"""LLM client factory — GroqClient, OpenRouterClient, or FakeLLM. [REQ-3.17–3.20, REQ-3.24–3.26]"""

from __future__ import annotations

import json
import re
import time
from collections import deque
from typing import Protocol

from telconet_sentinel.config import settings

# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_markdown_json(text: str) -> str:
    """Remove ```json ... ``` wrappers some models return despite json_object mode."""
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    return match.group(1) if match else text


# ── Protocol ─────────────────────────────────────────────────────────────────

class LLMClient(Protocol):
    def complete_json(self, system: str, user: str, temperature: float) -> str:
        ...


# ── Groq ─────────────────────────────────────────────────────────────────────

class GroqClient:
    """Thin wrapper around Groq SDK with timeout and 1× retry on 429/timeout."""

    def __init__(self) -> None:
        from groq import Groq
        if not settings.groq_api_key:
            raise EnvironmentError("GROQ_API_KEY is not set.")
        self._client = Groq(api_key=settings.groq_api_key,
                            timeout=settings.llm_timeout_s)
        self.model = settings.groq_model

    def complete_json(self, system: str, user: str, temperature: float) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        for attempt in range(2):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                return _strip_markdown_json(resp.choices[0].message.content or "")
            except Exception as exc:
                err_str = str(exc).lower()
                if attempt == 0 and ("429" in err_str or "rate" in err_str or "timeout" in err_str):
                    time.sleep(2)
                    continue
                raise
        return ""


# ── OpenRouter ────────────────────────────────────────────────────────────────

class OpenRouterClient:
    """OpenAI-compatible client pointed at OpenRouter. [REQ-3.24, REQ-3.25]"""

    def __init__(self) -> None:
        from openai import OpenAI
        if not settings.openrouter_api_key:
            raise EnvironmentError(
                "OPENROUTER_API_KEY is not set. "
                "Set it in .env or switch LLM_MODE to 'groq' or 'fake'."
            )
        self._client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout=settings.llm_timeout_s,
        )
        self.model = settings.openrouter_model

    def complete_json(self, system: str, user: str, temperature: float) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        for attempt in range(2):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                return _strip_markdown_json(resp.choices[0].message.content or "")
            except Exception as exc:
                err_str = str(exc).lower()
                if attempt == 0 and ("429" in err_str or "rate" in err_str or "timeout" in err_str):
                    time.sleep(2)
                    continue
                raise
        return ""


# ── FakeLLM ───────────────────────────────────────────────────────────────────

_FAKE_GENERATOR_RESPONSE = json.dumps({
    "incident_id": "INC-FAKE-001-20260101T0000",
    "device_id": "FAKE-001",
    "predicted_status": "Warning",
    "root_cause_hypothesis": "Simulated fiber degradation for testing.",
    "root_cause_category": "FIBER_DEGRADATION",
    "telemetry_evidence": [
        {"metric": "rx_optical_power_dbm", "observed_value": -26.0, "threshold": -25.0, "interpretation": "Warning"}
    ],
    "action_plan": [
        {"step_no": 1, "action": "Check ONT rx power", "sop_reference": {"sop_id": "SOP-FTTH-001", "step": 1}, "priority": "P1"}
    ],
    "confidence": 0.80,
    "status_flag": "OK",
    "iteration": 1,
})

_FAKE_JUDGE_APPROVED = json.dumps({
    "incident_id": "INC-FAKE-001-20260101T0000",
    "iteration": 1,
    "sop_faithfulness_score": 90,
    "telemetry_consistency_score": 88,
    "verdict": "APPROVED",
    "issues": [],
    "invalid_citations": [],
    "revision_instructions": "",
    "rationale": "All actions supported by SOP context.",
})

_FAKE_JUDGE_REVISION = json.dumps({
    "incident_id": "INC-FAKE-001-20260101T0000",
    "iteration": 1,
    "sop_faithfulness_score": 60,
    "telemetry_consistency_score": 75,
    "verdict": "REVISION_NEEDED",
    "issues": [{"type": "UNSUPPORTED_ACTION", "detail": "Action not in SOP.", "severity": "HIGH"}],
    "invalid_citations": [],
    "revision_instructions": "Remove unsupported actions.",
    "rationale": "One action not supported by provided SOP context.",
})


class FakeLLM:
    """Deterministic fake LLM for testing without API key or network."""

    def __init__(self, responses: list[str] | None = None) -> None:
        default = [_FAKE_GENERATOR_RESPONSE, _FAKE_JUDGE_APPROVED]
        self._queue: deque[str] = deque(responses or default)
        self.model = "fake"

    def complete_json(self, system: str, user: str, temperature: float) -> str:
        if self._queue:
            return self._queue.popleft()
        # Cycle: alternate generator / judge approved
        return _FAKE_JUDGE_APPROVED

    def push(self, response: str) -> None:
        self._queue.append(response)


# ── Factory ───────────────────────────────────────────────────────────────────

_fake_instance: FakeLLM | None = None


def get_llm(mode: str | None = None) -> LLMClient:
    global _fake_instance
    m = mode or settings.llm_mode
    if m == "fake":
        if _fake_instance is None:
            _fake_instance = FakeLLM()
        return _fake_instance
    if m == "groq":
        return GroqClient()
    if m == "openrouter":
        return OpenRouterClient()
    raise ValueError(
        f"Unknown LLM_MODE '{m}'. Valid values: 'groq', 'openrouter', 'fake'. "
        "Check your .env file."
    )


def reset_fake_llm(responses: list[str] | None = None) -> FakeLLM:
    """Helper for tests: reset fake LLM with custom response queue."""
    global _fake_instance
    _fake_instance = FakeLLM(responses)
    return _fake_instance
