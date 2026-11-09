import httpx
import pytest

from app.errors import IntegrationError
from app.services.weather_service import OpenMeteoProvider, WeatherService

PAYLOAD = {
    "latitude": 30.9,
    "longitude": 75.85,
    "timezone": "GMT",
    "current": {
        "time": "2026-11-09T12:00",
        "temperature_2m": 28.4,
        "relative_humidity_2m": 62,
        "precipitation": 0,
        "weather_code": 1,
        "wind_speed_10m": 9.5,
    },
    "hourly": {
        "time": ["2026-11-09T11:00", "2026-11-09T12:00"],
        "precipitation_probability": [10, 35],
    },
    "daily": {
        "time": ["2026-11-09"],
        "temperature_2m_max": [33.0],
        "temperature_2m_min": [21.0],
        "precipitation_sum": [4.2],
        "precipitation_probability_max": [40],
        "wind_speed_10m_max": [14.0],
        "weather_code": [2],
    },
}


def _service(handler, cache_seconds: int = 600) -> WeatherService:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return WeatherService(OpenMeteoProvider(client), cache_seconds=cache_seconds)


def test_normalizes_open_meteo_and_marks_nothing_unavailable():
    service = _service(lambda _request: httpx.Response(200, json=PAYLOAD))
    current = service.current(30.9, 75.85)
    assert current.temperature == 28.4
    assert current.humidity == 62
    assert current.rainfall == 0
    assert current.precipitation_probability == 35
    assert current.wind_speed == 9.5
    assert current.conditions == "Mainly clear"
    assert current.unavailable_fields == []
    assert current.stale is False
    forecast = service.forecast(30.9, 75.85)
    assert forecast.days[0].precipitation_sum == 4.2
    assert forecast.days[0].conditions == "Partly cloudy"


def test_missing_measurements_stay_null():
    payload = {
        "latitude": 19.9,
        "longitude": 73.8,
        "current": {"time": "2026-11-09T12:00", "weather_code": 999},
        "hourly": {"time": [], "precipitation_probability": []},
        "daily": {"time": []},
    }
    service = _service(lambda _request: httpx.Response(200, json=payload))
    current = service.current(19.9, 73.8)
    assert current.temperature is None
    assert current.rainfall is None
    assert current.precipitation_probability is None
    assert current.conditions == "Weather code 999"
    assert "temperature" in current.unavailable_fields
    assert "rainfall" in current.unavailable_fields


def test_provider_failure_without_cache_raises():
    service = _service(lambda _request: httpx.Response(503, json={"reason": "down"}))
    with pytest.raises(IntegrationError):
        service.current(30.9, 75.85)


def test_provider_failure_returns_stale_cache():
    calls = {"count": 0}

    def handler(_request):
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(200, json=PAYLOAD)
        return httpx.Response(503, json={"reason": "down"})

    service = _service(handler, cache_seconds=0)
    first = service.current(30.9, 75.85)
    second = service.current(30.9, 75.85)
    assert first.stale is False
    assert second.stale is True
    assert second.temperature == 28.4
    assert second.from_cache is True
