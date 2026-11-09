"""Open-Meteo client and response normalization.

Missing provider fields stay null. Weather-code text is a label for the
numeric code the provider returned, not a separate measurement.
"""

from datetime import datetime, timezone
from typing import Any

import httpx

from app.errors import IntegrationError
from app.schemas.weather import CurrentWeather, ForecastDay, ForecastWeather
from app.utils.time import utc_now

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def weather_code_label(code: Any) -> str | None:
    number = _num(code)
    if number is None:
        return None
    rounded = int(number)
    return WMO_CODES.get(rounded, f"Weather code {rounded}")


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _unavailable(values: dict[str, Any]) -> list[str]:
    return [name for name, value in values.items() if value is None]


def _hourly_probability(payload: dict, observation: str | None) -> float | None:
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    probabilities = hourly.get("precipitation_probability") or []
    if not times or not probabilities or not observation:
        return None
    hour = observation[:13]
    for stamp, probability in zip(times, probabilities):
        if str(stamp)[:13] == hour:
            return _num(probability)
    return None


def normalize_current(
    payload: dict,
    *,
    fetched_at: datetime,
    from_cache: bool,
    stale: bool,
) -> CurrentWeather:
    current = payload.get("current") or {}
    observation = current.get("time")
    measurements = {
        "temperature": _num(current.get("temperature_2m")),
        "humidity": _num(current.get("relative_humidity_2m")),
        "rainfall": _num(current.get("precipitation")),
        "precipitation_probability": _hourly_probability(payload, observation),
        "wind_speed": _num(current.get("wind_speed_10m")),
        "conditions": weather_code_label(current.get("weather_code")),
    }
    latitude = _num(payload.get("latitude"))
    longitude = _num(payload.get("longitude"))
    if latitude is None or longitude is None:
        raise IntegrationError("The weather provider returned no coordinates.")
    return CurrentWeather(
        latitude=latitude,
        longitude=longitude,
        provider="open-meteo",
        fetched_at=fetched_at,
        observation_time=_parse_time(observation),
        from_cache=from_cache,
        stale=stale,
        raw_payload=payload,
        unavailable_fields=_unavailable(measurements),
        **measurements,
    )


def normalize_forecast(
    payload: dict,
    *,
    fetched_at: datetime,
    from_cache: bool,
    stale: bool,
) -> ForecastWeather:
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    days: list[ForecastDay] = []
    missing: set[str] = set()
    fields = {
        "temperature_max": daily.get("temperature_2m_max") or [],
        "temperature_min": daily.get("temperature_2m_min") or [],
        "precipitation_sum": daily.get("precipitation_sum") or [],
        "precipitation_probability_max": daily.get("precipitation_probability_max") or [],
        "wind_speed_max": daily.get("wind_speed_10m_max") or [],
        "weather_code": daily.get("weather_code") or [],
    }
    for index, day in enumerate(dates):
        values = {name: _at(series, index) for name, series in fields.items()}
        for name, series in fields.items():
            if index >= len(series) or series[index] is None:
                missing.add(name)
        days.append(
            ForecastDay(
                date=str(day),
                temperature_max=_num(values["temperature_max"]),
                temperature_min=_num(values["temperature_min"]),
                precipitation_sum=_num(values["precipitation_sum"]),
                precipitation_probability_max=_num(values["precipitation_probability_max"]),
                wind_speed_max=_num(values["wind_speed_max"]),
                conditions=weather_code_label(values["weather_code"]),
            )
        )
    if not days:
        missing.update(fields)
    latitude = _num(payload.get("latitude"))
    longitude = _num(payload.get("longitude"))
    if latitude is None or longitude is None:
        raise IntegrationError("The weather provider returned no coordinates.")
    return ForecastWeather(
        latitude=latitude,
        longitude=longitude,
        timezone=payload.get("timezone"),
        provider="open-meteo",
        fetched_at=fetched_at,
        days=days,
        unavailable_fields=sorted(missing),
        from_cache=from_cache,
        stale=stale,
    )


def _at(values: list, index: int) -> Any:
    if index >= len(values):
        return None
    return values[index]


class OpenMeteoProvider:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def fetch(self, latitude: float, longitude: float) -> dict:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "UTC",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "forecast_days": 3,
            "current": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                ]
            ),
            "hourly": "precipitation_probability",
            "daily": ",".join(
                [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "precipitation_probability_max",
                    "wind_speed_10m_max",
                ]
            ),
        }
        client = self._client or httpx.Client(timeout=20)
        close_client = self._client is None
        try:
            response = client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise IntegrationError("The weather provider could not be reached.") from exc
        finally:
            if close_client:
                client.close()
        if not isinstance(payload, dict):
            raise IntegrationError("The weather provider returned an unexpected response.")
        return payload


class WeatherService:
    def __init__(self, provider: OpenMeteoProvider, cache_seconds: int = 600) -> None:
        self.provider = provider
        self.cache_seconds = cache_seconds
        self._cache: dict[tuple[float, float], tuple[datetime, dict]] = {}

    def current(self, latitude: float, longitude: float) -> CurrentWeather:
        payload, fetched_at, from_cache, stale = self._load(latitude, longitude)
        return normalize_current(
            payload,
            fetched_at=fetched_at,
            from_cache=from_cache,
            stale=stale,
        )

    def forecast(self, latitude: float, longitude: float) -> ForecastWeather:
        payload, fetched_at, from_cache, stale = self._load(latitude, longitude)
        return normalize_forecast(
            payload,
            fetched_at=fetched_at,
            from_cache=from_cache,
            stale=stale,
        )

    def _load(
        self, latitude: float, longitude: float
    ) -> tuple[dict, datetime, bool, bool]:
        key = (round(latitude, 3), round(longitude, 3))
        cached = self._cache.get(key)
        now = utc_now()
        if cached is not None:
            fetched_at, payload = cached
            age = (now - fetched_at).total_seconds()
            if age < self.cache_seconds:
                return payload, fetched_at, True, False
        try:
            payload = self.provider.fetch(latitude, longitude)
        except IntegrationError:
            if cached is not None:
                return cached[1], cached[0], True, True
            raise
        self._cache[key] = (now, payload)
        return payload, now, False, False
