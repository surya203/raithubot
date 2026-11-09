from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from app.utils.time import to_ist_iso


class CurrentWeather(BaseModel):
    latitude: float
    longitude: float
    temperature: float | None = None
    humidity: float | None = None
    rainfall: float | None = None
    precipitation_probability: float | None = None
    wind_speed: float | None = None
    conditions: str | None = None
    provider: str
    fetched_at: datetime
    observation_time: datetime | None = None
    unavailable_fields: list[str] = Field(default_factory=list)
    from_cache: bool = False
    stale: bool = False
    snapshot_stored: bool = False
    snapshot_note: str | None = None
    raw_payload: dict | None = Field(default=None, exclude=True)
    units: dict[str, str] = Field(
        default_factory=lambda: {
            "temperature": "celsius",
            "humidity": "percent",
            "rainfall": "millimetres",
            "precipitation_probability": "percent",
            "wind_speed": "kilometres_per_hour",
        }
    )

    @computed_field
    @property
    def fetched_at_ist(self) -> str | None:
        return to_ist_iso(self.fetched_at)

    @computed_field
    @property
    def observation_time_ist(self) -> str | None:
        return to_ist_iso(self.observation_time)


class ForecastDay(BaseModel):
    date: str
    temperature_max: float | None = None
    temperature_min: float | None = None
    precipitation_sum: float | None = None
    precipitation_probability_max: float | None = None
    wind_speed_max: float | None = None
    conditions: str | None = None


class ForecastWeather(BaseModel):
    latitude: float
    longitude: float
    timezone: str | None = None
    provider: str
    fetched_at: datetime
    days: list[ForecastDay] = Field(default_factory=list)
    unavailable_fields: list[str] = Field(default_factory=list)
    from_cache: bool = False
    stale: bool = False

    @computed_field
    @property
    def fetched_at_ist(self) -> str | None:
        return to_ist_iso(self.fetched_at)
