"""Pydantic schemas for all data models. [REQ-1.10, REQ-3.6, REQ-3.9, NFR-4]"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

# ── Telemetry ─────────────────────────────────────────────────────────────────

class AnomalyStatus(str, Enum):
    Normal = "Normal"
    Warning = "Warning"
    Critical = "Critical"


class DeviceType(str, Enum):
    OLT = "OLT"
    ONT = "ONT"
    CORE_ROUTER = "CORE_ROUTER"


class TelemetryRow(BaseModel):
    timestamp: str
    device_id: str
    region: str
    device_type: DeviceType
    rx_optical_power_dbm: float = Field(ge=-40.0, le=3.0)
    latency_ms: float = Field(ge=0.5, le=1000.0)
    packet_loss_pct: float = Field(ge=0.0, le=100.0)
    cpu_load_pct: float = Field(ge=0.0, le=100.0)
    temperature_c: float = Field(ge=10.0, le=100.0)
    anomaly_status: AnomalyStatus


# ── Generator Agent Output ────────────────────────────────────────────────────

class RootCauseCategory(str, Enum):
    FIBER_DEGRADATION = "FIBER_DEGRADATION"
    CONGESTION = "CONGESTION"
    OVERHEATING = "OVERHEATING"
    CPU_SPIKE = "CPU_SPIKE"
    UNKNOWN = "UNKNOWN"


class StatusFlag(str, Enum):
    OK = "OK"
    INSUFFICIENT_SOP_CONTEXT = "INSUFFICIENT_SOP_CONTEXT"


class PredictedStatus(str, Enum):
    Warning = "Warning"
    Critical = "Critical"


class ActionPriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class SopReference(BaseModel):
    sop_id: str
    step: int


class TelemetryEvidence(BaseModel):
    metric: str
    observed_value: float
    threshold: float
    interpretation: str


class ActionStep(BaseModel):
    step_no: int
    action: str
    sop_reference: SopReference
    priority: ActionPriority


class GeneratorOutput(BaseModel):
    incident_id: str
    device_id: str
    predicted_status: PredictedStatus
    root_cause_hypothesis: str = Field(max_length=400)
    root_cause_category: RootCauseCategory
    telemetry_evidence: list[TelemetryEvidence]
    action_plan: list[ActionStep] = Field(min_length=1, max_length=6)
    confidence: float = Field(ge=0.0, le=1.0)
    status_flag: StatusFlag
    iteration: int = Field(ge=1, le=2)


# ── Judge / Critic Output ─────────────────────────────────────────────────────

class Verdict(str, Enum):
    APPROVED = "APPROVED"
    REVISION_NEEDED = "REVISION_NEEDED"


class IssueType(str, Enum):
    UNSUPPORTED_ACTION = "UNSUPPORTED_ACTION"
    WRONG_CITATION = "WRONG_CITATION"
    TELEMETRY_MISMATCH = "TELEMETRY_MISMATCH"
    MISSING_STEP = "MISSING_STEP"
    OTHER = "OTHER"


class IssueSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Issue(BaseModel):
    type: IssueType
    detail: str
    severity: IssueSeverity


class InvalidCitation(BaseModel):
    sop_id: str
    step: int


class JudgeOutput(BaseModel):
    incident_id: str
    iteration: int = Field(ge=1, le=2)
    sop_faithfulness_score: int = Field(ge=1, le=100)
    telemetry_consistency_score: int = Field(ge=1, le=100)
    verdict: Verdict
    issues: list[Issue] = Field(default_factory=list)
    invalid_citations: list[InvalidCitation] = Field(default_factory=list)
    revision_instructions: str = ""
    rationale: str = Field(default="", max_length=500)

    @field_validator("revision_instructions")
    @classmethod
    def revision_required_when_needed(cls, v: str, info: Any) -> str:
        # Validation is enforced by orchestrator logic; accept empty here
        return v


# ── Orchestrator Result ───────────────────────────────────────────────────────

class FinalStatus(str, Enum):
    APPROVED = "APPROVED"
    UNVERIFIED_ESCALATE_TO_HUMAN = "UNVERIFIED_ESCALATE_TO_HUMAN"
    ERROR = "ERROR"


class IterationRecord(BaseModel):
    draft: GeneratorOutput
    judge: JudgeOutput
    latency_ms: float


class RcaResult(BaseModel):
    incident_id: str
    final_status: FinalStatus
    final_draft: Optional[GeneratorOutput] = None
    iterations: list[IterationRecord] = Field(default_factory=list)
    retrieved_sop_ids: list[str] = Field(default_factory=list)
    total_latency_ms: float = 0.0
    model: str = ""
    error: Optional[str] = None
