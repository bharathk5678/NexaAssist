from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.answer import AnswerResponse
from app.models.retrieval import RetrieveRequest

MetricName = Literal["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
METRIC_NAMES: tuple[MetricName, ...] = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)


class EvaluatedAnswerRequest(RetrieveRequest):
    reference_answer: str | None = Field(default=None, min_length=1, max_length=8000)


class QualityScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["scored", "unavailable", "error"]
    value: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    reason: str | None = None

    @field_validator("value", mode="before")
    @classmethod
    def normalize_roundoff(cls, value: object) -> object:
        # Cosine similarity can produce 1.0000000000000002 for identical vectors.
        # Only tolerate numerical roundoff; materially invalid scores still fail.
        if isinstance(value, float):
            if 1 < value <= 1 + 1e-12:
                return 1.0
            if -1e-12 <= value < 0:
                return 0.0
        return value

    @model_validator(mode="after")
    def score_matches_status(self) -> QualityScore:
        if (self.status == "scored") != (self.value is not None):
            raise ValueError("Only scored metrics can contain a value")
        return self


class AnswerQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: dict[MetricName, QualityScore]
    reference_source: Literal["provided", "golden_dataset", "none"]
    reference_answer: str | None = None
    evaluated_at: datetime
    datadog_status: Literal["disabled", "queued", "not_scored", "error"] = "disabled"
    datadog_url: str | None = None

    @model_validator(mode="after")
    def all_metrics_present(self) -> AnswerQuality:
        if set(self.metrics) != set(METRIC_NAMES):
            raise ValueError("Every quality metric requires a score or an explicit status")
        return self


class EvaluatedAnswerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: AnswerResponse
    quality: AnswerQuality
