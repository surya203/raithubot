import re

from app.config import Settings
from app.schemas.alerts import AlertDraft
from app.schemas.weather import CurrentWeather, ForecastWeather

THRESHOLD_NOTE = (
    "This threshold is an application heuristic for internal awareness. "
    "It is not a calibrated disease prediction or an official IMD warning."
)


def detect_alerts(
    settings: Settings,
    *,
    crop_name: str | None,
    current: CurrentWeather | None,
    forecast: ForecastWeather | None,
    soil_moisture: float | None,
    symptoms: str | None,
) -> list[AlertDraft]:
    drafts: list[AlertDraft] = []
    rain = _heavy_rain(settings, current, forecast)
    if rain is not None:
        drafts.append(rain)
    temperature = _temperature(settings, current, forecast)
    if temperature is not None:
        drafts.append(temperature)
    humidity = _humidity(settings, crop_name, current)
    if humidity is not None:
        drafts.append(humidity)
    moisture = _soil_moisture(settings, soil_moisture)
    if moisture is not None:
        drafts.append(moisture)
    reported = _symptoms(symptoms)
    if reported is not None:
        drafts.append(reported)
    return drafts


def _heavy_rain(
    settings: Settings,
    current: CurrentWeather | None,
    forecast: ForecastWeather | None,
) -> AlertDraft | None:
    current_rain = current.rainfall if current else None
    matched_day = None
    matched_amount = None
    matched_probability = None
    if forecast is not None:
        for day in forecast.days:
            amount = day.precipitation_sum
            probability = day.precipitation_probability_max
            if amount is not None and amount >= settings.alert_heavy_rain_mm:
                matched_day = day.date
                matched_amount = amount
                matched_probability = probability
                break
            if (
                amount is not None
                and probability is not None
                and amount >= settings.alert_heavy_rain_min_mm_with_probability
                and probability >= settings.alert_heavy_rain_probability
            ):
                matched_day = day.date
                matched_amount = amount
                matched_probability = probability
                break
    if matched_amount is None and current_rain is not None and current_rain >= settings.alert_heavy_rain_mm:
        matched_amount = current_rain
    if matched_amount is None:
        return None
    severity = "high" if matched_amount >= settings.alert_heavy_rain_mm else "moderate"
    return AlertDraft(
        title="Heavy rainfall condition",
        description=(
            f"A rainfall amount of {matched_amount:g} mm met the internal heavy-rain rule. "
            f"{THRESHOLD_NOTE}"
        ),
        category="rainfall",
        severity=severity,
        supporting_context={
            "threshold_note": THRESHOLD_NOTE,
            "heavy_rain_mm": settings.alert_heavy_rain_mm,
            "observed_mm": matched_amount,
            "forecast_date": matched_day,
            "precipitation_probability": matched_probability,
            "current_rainfall_mm": current_rain,
        },
    )


def _temperature(
    settings: Settings,
    current: CurrentWeather | None,
    forecast: ForecastWeather | None,
) -> AlertDraft | None:
    current_temp = current.temperature if current else None
    hottest = current_temp
    coldest = current_temp
    if forecast is not None:
        maxima = [day.temperature_max for day in forecast.days if day.temperature_max is not None]
        minima = [day.temperature_min for day in forecast.days if day.temperature_min is not None]
        if maxima:
            hottest = max([value for value in [hottest, max(maxima)] if value is not None], default=None)
        if minima:
            coldest = min([value for value in [coldest, min(minima)] if value is not None], default=None)
    hot = hottest is not None and hottest >= settings.alert_extreme_heat_c
    cold = coldest is not None and coldest <= settings.alert_extreme_cold_c
    if not hot and not cold:
        return None
    if hot and cold:
        return AlertDraft(
            title="Extreme temperature condition",
            description=(
                f"Temperature reached {hottest:g} °C and {coldest:g} °C, "
                f"meeting both internal bounds. {THRESHOLD_NOTE}"
            ),
            category="temperature",
            severity="high",
            supporting_context={
                "threshold_note": THRESHOLD_NOTE,
                "heat_c": settings.alert_extreme_heat_c,
                "cold_c": settings.alert_extreme_cold_c,
                "observed_hot_c": hottest,
                "observed_cold_c": coldest,
                "current_temperature_c": current_temp,
            },
        )
    if hot:
        title = "High temperature condition"
        observed = hottest
        bound = "heat"
    else:
        title = "Low temperature condition"
        observed = coldest
        bound = "cold"
    return AlertDraft(
        title=title,
        description=(
            f"The {bound} rule was met at {observed:g} °C. {THRESHOLD_NOTE}"
        ),
        category="temperature",
        severity="high",
        supporting_context={
            "threshold_note": THRESHOLD_NOTE,
            "heat_c": settings.alert_extreme_heat_c,
            "cold_c": settings.alert_extreme_cold_c,
            "observed_c": observed,
            "current_temperature_c": current_temp,
        },
    )


def _humidity(
    settings: Settings,
    crop_name: str | None,
    current: CurrentWeather | None,
) -> AlertDraft | None:
    humidity = current.humidity if current else None
    if crop_name is None or humidity is None or humidity < settings.alert_high_humidity:
        return None
    if not _crop_matches(crop_name, settings.humidity_crop_names):
        return None
    return AlertDraft(
        title="High humidity on a susceptible crop",
        description=(
            f"Relative humidity is {humidity:g}% for {crop_name}. "
            "This can be a reason to inspect the crop. It does not confirm a disease. "
            f"{THRESHOLD_NOTE}"
        ),
        category="humidity",
        severity="moderate",
        supporting_context={
            "threshold_note": THRESHOLD_NOTE,
            "humidity_percent": humidity,
            "humidity_threshold": settings.alert_high_humidity,
            "crop_name": crop_name,
            "susceptible_names": sorted(settings.humidity_crop_names),
        },
    )


def _soil_moisture(settings: Settings, soil_moisture: float | None) -> AlertDraft | None:
    if soil_moisture is None or soil_moisture > settings.alert_low_soil_moisture:
        return None
    return AlertDraft(
        title="Low reported soil moisture",
        description=(
            f"The operator-reported soil moisture value is {soil_moisture:g}, "
            f"at or below the internal value {settings.alert_low_soil_moisture:g}. "
            "The unit is the unit used when the value was entered. "
            f"{THRESHOLD_NOTE}"
        ),
        category="soil_moisture",
        severity="moderate",
        supporting_context={
            "threshold_note": THRESHOLD_NOTE,
            "soil_moisture": soil_moisture,
            "threshold": settings.alert_low_soil_moisture,
        },
    )


def _symptoms(symptoms: str | None) -> AlertDraft | None:
    text = (symptoms or "").strip()
    if not text:
        return None
    return AlertDraft(
        title="Farmer-reported symptoms",
        description=(
            "Symptoms were reported for this crop. This is a field report, not a diagnosis. "
            f"{THRESHOLD_NOTE}"
        ),
        category="disease_symptoms",
        severity="moderate",
        supporting_context={
            "threshold_note": THRESHOLD_NOTE,
            "symptoms": text[:1000],
        },
    )


def _crop_matches(crop_name: str, names: set[str]) -> bool:
    lowered = crop_name.lower()
    return any(re.search(rf"\b{re.escape(name)}\b", lowered) for name in names)
