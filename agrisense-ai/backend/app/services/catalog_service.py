from __future__ import annotations

from uuid import UUID

from app.repositories.records import RecordsRepository
from app.schemas.crops import CropCreate, CropRead, LocationCreate, LocationRead
from app.schemas.environment import EnvironmentCreate, EnvironmentRead
from app.schemas.weather import CurrentWeather
from app.utils.time import utc_now


class LocationService:
    def __init__(self, records: RecordsRepository) -> None:
        self.records = records

    def create(self, payload: LocationCreate) -> LocationRead:
        row = self.records.create_location(payload.model_dump(mode="json"))
        return LocationRead.model_validate(row)

    def list(self) -> list[LocationRead]:
        return [LocationRead.model_validate(row) for row in self.records.list_locations()]

    def get(self, location_id: UUID) -> LocationRead:
        return LocationRead.model_validate(self.records.get_location(location_id))


class CropService:
    def __init__(self, records: RecordsRepository) -> None:
        self.records = records

    def create(self, payload: CropCreate) -> CropRead:
        self.records.get_location(payload.location_id)
        row = self.records.create_crop(payload.model_dump(mode="json"))
        return CropRead.model_validate(row)

    def list(self, location_id: UUID | None = None) -> list[CropRead]:
        return [CropRead.model_validate(row) for row in self.records.list_crops(location_id)]

    def get(self, crop_id: UUID) -> CropRead:
        return CropRead.model_validate(self.records.get_crop(crop_id))

    def update(self, crop_id: UUID, payload: CropCreate) -> CropRead:
        self.records.get_location(payload.location_id)
        row = self.records.update_crop(crop_id, payload.model_dump(mode="json"))
        return CropRead.model_validate(row)

    def delete(self, crop_id: UUID) -> None:
        self.records.delete_crop(crop_id)


class EnvironmentService:
    def __init__(self, records: RecordsRepository) -> None:
        self.records = records

    def create(self, payload: EnvironmentCreate) -> EnvironmentRead:
        data = payload.model_dump(mode="json")
        if not data.get("recorded_at"):
            data["recorded_at"] = utc_now().isoformat()
        row = self.records.create_environment(data)
        return EnvironmentRead.model_validate(row)

    def list(
        self,
        location_id: UUID | None = None,
        crop_id: UUID | None = None,
        limit: int = 50,
    ) -> list[EnvironmentRead]:
        rows = self.records.list_environment(location_id, crop_id, limit)
        return [EnvironmentRead.model_validate(row) for row in rows]

    def store_weather(
        self,
        location_id: UUID,
        crop_id: UUID | None,
        weather: CurrentWeather,
    ) -> EnvironmentRead:
        recorded = weather.observation_time or weather.fetched_at
        payload = EnvironmentCreate(
            location_id=location_id,
            crop_id=crop_id,
            temperature=weather.temperature,
            humidity=weather.humidity,
            rainfall=weather.rainfall,
            precipitation_probability=weather.precipitation_probability,
            wind_speed=weather.wind_speed,
            conditions=weather.conditions,
            source="open-meteo",
            raw_payload=weather.raw_payload,
            recorded_at=recorded,
        )
        return self.create(payload)

    def latest_soil_moisture(self, location_id: UUID) -> float | None:
        rows = self.records.list_environment(location_id=location_id, limit=20)
        for row in rows:
            value = row.get("soil_moisture")
            if value is not None:
                return float(value)
        return None
