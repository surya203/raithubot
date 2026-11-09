from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator

from app.schemas.common import Timestamped
from app.utils.time import to_ist_iso


class EnvironmentCreate(BaseModel):
    location_id: UUID
    crop_id: UUID | None = None
    temperature: float | None = None
    humidity: float | None = Field(default=None, ge=0, le=100)
    rainfall: float | None = Field(default=None, ge=0)
    precipitation_probability: float | None = Field(default=None, ge=0, le=100)
    wind_speed: float | None = Field(default=None, ge=0)
    soil_moisture: float | None = Field(default=None, ge=0)
    soil_ph: float | None = Field(default=None, ge=0, le=14)
    conditions: str | None = None
    source: str = Field(min_length=1)
    raw_payload: dict | None = None
    recorded_at: datetime | None = None

    @field_validator("source", "conditions")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("This field cannot be blank.")
        return text


class EnvironmentRead(EnvironmentCreate, Timestamped):
    id: UUID
    recorded_at: datetime

    @computed_field
    @property
    def recorded_at_ist(self) -> str | None:
        return to_ist_iso(self.recorded_at)
