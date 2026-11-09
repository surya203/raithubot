from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import Timestamped

AdvisoryType = Literal[
    "crop_management",
    "disease_prevention",
    "chatbot",
    "alert_explanation",
]
RiskLevel = Literal["low", "moderate", "high", "insufficient_evidence"]
DiseaseStatus = Literal[
    "environmental_risk",
    "suspected_from_symptoms",
    "not_assessed",
]


class EvidenceItem(BaseModel):
    title: str
    source_organization: str | None = None
    document_url: str | None = None
    excerpt: str | None = None


class AdvisoryBody(BaseModel):
    crop: str
    growth_stage: str | None = None
    advisory_type: str
    risk_level: RiskLevel
    observations: list[str] = Field(default_factory=list)
    possible_concerns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    disease_status: DiseaseStatus | None = None


class CropAdvisoryRequest(BaseModel):
    crop_id: UUID


class DiseaseAdvisoryRequest(BaseModel):
    crop_id: UUID
    symptoms: str = ""


class AdvisoryRead(Timestamped):
    id: UUID
    crop_id: UUID | None = None
    location_id: UUID | None = None
    advisory_type: AdvisoryType
    input_context: dict
    advisory_response: dict
    retrieved_sources: list


class AdvisoryHistoryQuery(BaseModel):
    crop_id: UUID | None = None
    advisory_type: AdvisoryType | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=50, ge=1, le=200)
