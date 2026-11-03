"""Pydantic schema validation tests. [REQ-3.6, 3.9, NFR-4]"""

import pytest
from pydantic import ValidationError

from telconet_sentinel.schemas import GeneratorOutput, JudgeOutput

VALID_GENERATOR_JSON = """{
  "incident_id": "INC-ONT-BDG-017-20260101T1335",
  "device_id": "ONT-BDG-017",
  "predicted_status": "Critical",
  "root_cause_hypothesis": "Redaman optik naik bertahap ~8 dB dalam 1 jam.",
  "root_cause_category": "FIBER_DEGRADATION",
  "telemetry_evidence": [
    {"metric": "rx_optical_power_dbm", "observed_value": -28.62, "threshold": -28.0, "interpretation": "Melewati ambang Critical"}
  ],
  "action_plan": [
    {"step_no": 1, "action": "Verifikasi rx power ONT dari NMS", "sop_reference": {"sop_id": "SOP-FTTH-001", "step": 1}, "priority": "P1"}
  ],
  "confidence": 0.78,
  "status_flag": "OK",
  "iteration": 1
}"""

VALID_JUDGE_JSON = """{
  "incident_id": "INC-ONT-BDG-017-20260101T1335",
  "iteration": 1,
  "sop_faithfulness_score": 64,
  "telemetry_consistency_score": 90,
  "verdict": "REVISION_NEEDED",
  "issues": [
    {"type": "UNSUPPORTED_ACTION", "detail": "Action not in SOP.", "severity": "HIGH"}
  ],
  "invalid_citations": [
    {"sop_id": "SOP-FTTH-001", "step": 7}
  ],
  "revision_instructions": "Fix the citation.",
  "rationale": "Diagnosis ok but one citation missing."
}"""


def test_generator_output_valid():
    obj = GeneratorOutput.model_validate_json(VALID_GENERATOR_JSON)
    assert obj.incident_id == "INC-ONT-BDG-017-20260101T1335"


def test_judge_output_valid():
    obj = JudgeOutput.model_validate_json(VALID_JUDGE_JSON)
    assert obj.verdict.value == "REVISION_NEEDED"


def test_faithfulness_score_zero_rejected():
    import json
    data = json.loads(VALID_JUDGE_JSON)
    data["sop_faithfulness_score"] = 0
    with pytest.raises(ValidationError):
        JudgeOutput.model_validate(data)


def test_faithfulness_score_101_rejected():
    import json
    data = json.loads(VALID_JUDGE_JSON)
    data["sop_faithfulness_score"] = 101
    with pytest.raises(ValidationError):
        JudgeOutput.model_validate(data)


def test_generator_confidence_out_of_range():
    import json
    data = json.loads(VALID_GENERATOR_JSON)
    data["confidence"] = 1.5
    with pytest.raises(ValidationError):
        GeneratorOutput.model_validate(data)


def test_generator_hypothesis_too_long():
    import json
    data = json.loads(VALID_GENERATOR_JSON)
    data["root_cause_hypothesis"] = "x" * 401
    with pytest.raises(ValidationError):
        GeneratorOutput.model_validate(data)
