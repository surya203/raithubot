from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import Timestamped

AlertCategory = Literal[
    "rainfall",
    "temperature",
    "humidity",
    "soil_moisture",
    "disease_symptoms",
]
AlertSeverity = Literal["info", "low", "moderate", "high"]


class AlertExplanation(BaseModel):
    title: str
    description: str
    suggested_action: str = ""
    limitations: list[str] = Field(default_factory=list)


class AlertDraft(BaseModel):
    title: str
    description: str
    category: AlertCategory
    severity: AlertSeverity
    supporting_context: dict = Field(default_factory=dict)


class AlertEvaluateRequest(BaseModel):
    location_id: UUID
    crop_id: UUID | None = None
    symptoms: str | None = None


class AlertRead(Timestamped):
    id: UUID
    crop_id: UUID | None = None
    location_id: UUID | None = None
    title: str
    description: str
    category: AlertCategory
    severity: AlertSeverity
    supporting_context: dict
    is_read: bool
