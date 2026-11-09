from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import get_settings
from app.dependencies import get_weather_service
from app.knowledge.chunking import chunk_pages
from app.knowledge.extract import extract_pages
from app.main import app
from app.schemas.crops import CropCreate
from app.schemas.weather import CurrentWeather, ForecastWeather
from app.utils.time import utc_now

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_internal_token(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_TOKEN", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class StubWeather:
    def current(self, latitude: float, longitude: float) -> CurrentWeather:
        return CurrentWeather(
            latitude=latitude,
            longitude=longitude,
            provider="open-meteo",
            fetched_at=utc_now(),
            temperature=29.0,
            humidity=None,
            rainfall=None,
            conditions="Mainly clear",
            unavailable_fields=["humidity", "rainfall"],
        )

    def forecast(self, latitude: float, longitude: float) -> ForecastWeather:
        return ForecastWeather(
            latitude=latitude,
            longitude=longitude,
            provider="open-meteo",
            fetched_at=utc_now(),
            days=[],
            unavailable_fields=["temperature_max"],
        )


def test_health_reports_configuration_without_secrets():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["app"] == "AgriSense AI"
    assert body["status"] == "ok"
    assert isinstance(body["database_configured"], bool)
    assert isinstance(body["llm_configured"], bool)
    assert "api_key" not in response.text
    assert "service_role" not in response.text


def test_weather_requires_coordinates():
    response = client.get("/api/weather/current")
    assert response.status_code == 422
    assert "latitude" in response.json()["detail"]


def test_weather_uses_the_provider_result():
    app.dependency_overrides[get_weather_service] = lambda: StubWeather()
    response = client.get("/api/weather/current", params={"latitude": 30.9, "longitude": 75.8})
    assert response.status_code == 200
    body = response.json()
    assert body["temperature"] == 29.0
    assert body["humidity"] is None
    assert "humidity" in body["unavailable_fields"]
    assert "raw_payload" not in body
    assert body["fetched_at_ist"]
    app.dependency_overrides.pop(get_weather_service, None)


def test_internal_token_protects_api_and_leaves_health_open(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_TOKEN", "secret-token")
    get_settings.cache_clear()
    try:
        blocked = client.get("/api/weather/current")
        assert blocked.status_code == 401
        health = client.get("/api/health")
        assert health.status_code == 200
        allowed = client.get(
            "/api/weather/current",
            headers={"X-Internal-Token": "secret-token"},
        )
        assert allowed.status_code == 422
    finally:
        get_settings.cache_clear()


def test_crop_rejects_a_harvest_before_sowing():
    with pytest.raises(ValidationError):
        CropCreate(
            location_id=uuid4(),
            crop_name="Paddy",
            sowing_date=date(2026, 7, 1),
            expected_harvest_date=date(2026, 6, 1),
            growth_stage="vegetative",
            soil_type="clay",
            irrigation_method="canal",
        )


def test_text_extraction_and_chunking_keep_page_numbers():
    pages = extract_pages("note.txt", "text/plain", b"First paragraph.\n\nSecond paragraph.")
    chunks = chunk_pages(pages, size=20, overlap=5)
    assert pages[0][0] == 1
    assert chunks
    assert all(chunk.page_number == 1 for chunk in chunks)
    assert "First paragraph." in chunks[0].content
