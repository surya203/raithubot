from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import get_environment_service, get_location_service, get_weather_service
from app.errors import AppError
from app.schemas.weather import CurrentWeather, ForecastWeather
from app.services.weather_service import WeatherService

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/current", response_model=CurrentWeather)
def current_weather(
    latitude: float | None = None,
    longitude: float | None = None,
    location_id: UUID | None = None,
    crop_id: UUID | None = None,
    weather: WeatherService = Depends(get_weather_service),
) -> CurrentWeather:
    location, latitude, longitude = _coordinates(latitude, longitude, location_id)
    current = weather.current(latitude, longitude)
    if location is None:
        return current
    if current.from_cache:
        return current.model_copy(
            update={"snapshot_note": "Cached weather was not written again."}
        )
    try:
        get_environment_service().store_weather(location.id, crop_id, current)
    except AppError as exc:
        return current.model_copy(update={"snapshot_stored": False, "snapshot_note": exc.message})
    return current.model_copy(update={"snapshot_stored": True})


@router.get("/forecast", response_model=ForecastWeather)
def forecast_weather(
    latitude: float | None = None,
    longitude: float | None = None,
    location_id: UUID | None = None,
    weather: WeatherService = Depends(get_weather_service),
) -> ForecastWeather:
    _location, latitude, longitude = _coordinates(latitude, longitude, location_id)
    return weather.forecast(latitude, longitude)


def _coordinates(latitude: float | None, longitude: float | None, location_id: UUID | None):
    if location_id is not None:
        location = get_location_service().get(location_id)
        return location, location.latitude, location.longitude
    if latitude is None or longitude is None:
        raise AppError("Provide latitude and longitude, or a location_id.", status_code=422)
    return None, latitude, longitude
