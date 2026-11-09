from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from app.schemas.common import Timestamped
from app.utils.time import to_ist_iso

GrowthStage = Literal[
    "seedling",
    "vegetative",
    "flowering",
    "fruiting",
    "maturity",
    "harvest",
]


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class LocationCreate(BaseModel):
    name: str = Field(min_length=1)
    state: str = Field(min_length=1)
    district: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @field_validator("name", "state", "district")
    @classmethod
    def strip_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("This field cannot be blank.")
        return text


class LocationRead(LocationCreate, Timestamped):
    id: UUID


class CropCreate(BaseModel):
    location_id: UUID
    crop_name: str = Field(min_length=1)
    variety: str | None = None
    sowing_date: date
    expected_harvest_date: date | None = None
    growth_stage: GrowthStage
    soil_type: str = Field(min_length=1)
    soil_ph: float | None = Field(default=None, ge=0, le=14)
    nitrogen: float | None = Field(default=None, ge=0)
    phosphorus: float | None = Field(default=None, ge=0)
    potassium: float | None = Field(default=None, ge=0)
    irrigation_method: str = Field(min_length=1)
    observations: str | None = None

    @field_validator("crop_name", "soil_type", "irrigation_method")
    @classmethod
    def strip_required(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("This field cannot be blank.")
        return text

    @field_validator("variety", "observations")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @model_validator(mode="after")
    def harvest_after_sowing(self) -> "CropCreate":
        if (
            self.expected_harvest_date is not None
            and self.expected_harvest_date < self.sowing_date
        ):
            raise ValueError("expected_harvest_date must be on or after sowing_date.")
        return self


class CropUpdate(CropCreate):
    pass


class CropRead(CropCreate, Timestamped):
    id: UUID
    updated_at: datetime
    location_name: str | None = None

    @computed_field
    @property
    def updated_at_ist(self) -> str | None:
        return to_ist_iso(self.updated_at)
