from datetime import datetime, timezone

from app.config import Settings
from app.schemas.weather import CurrentWeather, ForecastDay, ForecastWeather
from app.services.alert_rules import detect_alerts

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


def settings() -> Settings:
    return Settings.model_construct(
        alert_heavy_rain_mm=50,
        alert_heavy_rain_probability=80,
        alert_heavy_rain_min_mm_with_probability=20,
        alert_extreme_heat_c=40,
        alert_extreme_cold_c=5,
        alert_high_humidity=85,
        alert_low_soil_moisture=30,
        alert_humidity_crops="rice,paddy,tomato,potato,cotton,grape",
        alert_dedupe_hours=12,
    )


def current(**overrides) -> CurrentWeather:
    values = {
        "latitude": 30.9,
        "longitude": 75.8,
        "provider": "open-meteo",
        "fetched_at": NOW,
        "temperature": 30,
        "humidity": 60,
        "rainfall": 0,
        "precipitation_probability": 10,
        "wind_speed": 8,
        "conditions": "Clear sky",
    }
    values.update(overrides)
    return CurrentWeather(**values)


def forecast(amount=None, probability=None, hot=None, cold=None) -> ForecastWeather:
    return ForecastWeather(
        latitude=30.9,
        longitude=75.8,
        provider="open-meteo",
        fetched_at=NOW,
        days=[
            ForecastDay(
                date="2026-11-10",
                precipitation_sum=amount,
                precipitation_probability_max=probability,
                temperature_max=hot,
                temperature_min=cold,
            )
        ],
    )


def categories(**kwargs) -> set[str]:
    return {draft.category for draft in detect_alerts(settings(), **kwargs)}


def test_missing_values_do_not_create_weather_alerts():
    found = categories(
        crop_name="Wheat",
        current=current(temperature=None, humidity=None, rainfall=None),
        forecast=None,
        soil_moisture=None,
        symptoms=None,
    )
    assert found == set()


def test_heavy_rain_and_heat_rules():
    found = categories(
        crop_name="Wheat",
        current=current(temperature=41, rainfall=0),
        forecast=forecast(amount=64),
        soil_moisture=None,
        symptoms=None,
    )
    assert found == {"rainfall", "temperature"}


def test_humidity_rule_matches_crop_name_only():
    humid = current(humidity=90)
    assert "humidity" in categories(
        crop_name="Basmati rice",
        current=humid,
        forecast=None,
        soil_moisture=None,
        symptoms=None,
    )
    assert "humidity" not in categories(
        crop_name="Wheat",
        current=humid,
        forecast=None,
        soil_moisture=None,
        symptoms=None,
    )


def test_soil_and_symptoms_require_real_inputs():
    assert categories(
        crop_name="Tomato",
        current=current(),
        forecast=None,
        soil_moisture=None,
        symptoms="   ",
    ) == set()
    found = categories(
        crop_name="Tomato",
        current=current(),
        forecast=None,
        soil_moisture=12,
        symptoms="Yellow leaves with spots",
    )
    assert found == {"soil_moisture", "disease_symptoms"}
