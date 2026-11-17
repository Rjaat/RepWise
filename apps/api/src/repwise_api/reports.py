from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Assessability = Literal["assessed", "not_assessable", "uncertain"]


class ImmutableModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ReportMetric(ImmutableModel):
    id: str
    label: str
    unit: str
    state: Assessability
    value: float | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_assessability(self) -> ReportMetric:
        if self.state == "assessed" and self.value is None:
            raise ValueError("Assessed metrics require a value")
        if self.state != "assessed" and self.value is not None:
            raise ValueError("Unavailable metrics cannot contain a value")
        if self.state != "assessed" and not self.reason:
            raise ValueError("Unavailable metrics require a reason")
        return self


class EvidenceLink(ImmutableModel):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_interval(self) -> EvidenceLink:
        if self.end_seconds < self.start_seconds:
            raise ValueError("Evidence end must follow its start")
        return self


class ReportRep(ImmutableModel):
    index: int = Field(gt=0)
    complete: bool
    evidence: EvidenceLink
    metrics: tuple[ReportMetric, ...]


class EvidenceReport(ImmutableModel):
    schema_version: Literal["repwise.evidence-report.v1"]
    analysis_id: str
    exercise: str
    variant: str
    view: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pose_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    segmentation_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reps: tuple[ReportRep, ...]

    def canonical_payload(self) -> bytes:
        return json.dumps(
            self.model_dump(), separators=(",", ":"), sort_keys=True
        ).encode()

    def checksum(self) -> str:
        return hashlib.sha256(self.canonical_payload()).hexdigest()
