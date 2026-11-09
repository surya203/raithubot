from __future__ import annotations

import logging
from uuid import UUID

from app.config import Settings
from app.errors import AppError, IntegrationError
from app.repositories.records import RecordsRepository
from app.schemas.alerts import AlertEvaluateRequest, AlertRead
from app.schemas.weather import CurrentWeather, ForecastWeather
from app.services.alert_rules import detect_alerts
from app.services.catalog_service import EnvironmentService
from app.services.llm_service import LLMService
from app.services.prompt_manager import PromptManager
from app.services.response_validator import validate_alert_explanation
from app.services.weather_service import WeatherService

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(
        self,
        records: RecordsRepository,
        weather: WeatherService,
        environment: EnvironmentService,
        llm: LLMService,
        prompts: PromptManager,
        settings: Settings,
    ) -> None:
        self.records = records
        self.weather = weather
        self.environment = environment
        self.llm = llm
        self.prompts = prompts
        self.settings = settings

    def list(
        self,
        crop_id: UUID | None = None,
        location_id: UUID | None = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[AlertRead]:
        rows = self.records.list_alerts(crop_id, location_id, unread_only, limit)
        return [AlertRead.model_validate(row) for row in rows]

    def mark_read(self, alert_id: UUID) -> AlertRead:
        return AlertRead.model_validate(self.records.mark_alert_read(alert_id))

    def evaluate(
        self,
        request: AlertEvaluateRequest,
        *,
        current: CurrentWeather | None = None,
        forecast: ForecastWeather | None = None,
        fetch_weather: bool = True,
    ) -> list[AlertRead]:
        location = self.records.get_location(request.location_id)
        if request.crop_id is not None:
            crops = [self.records.get_crop(request.crop_id)]
        else:
            crops = self.records.list_crops(request.location_id)
        if current is None and fetch_weather:
            try:
                current = self.weather.current(float(location["latitude"]), float(location["longitude"]))
                forecast = self.weather.forecast(float(location["latitude"]), float(location["longitude"]))
            except IntegrationError:
                logger.info("Weather was unavailable while evaluating alerts.")
                current = None
                forecast = None
        soil = self.environment.latest_soil_moisture(request.location_id)
        targets = crops or [None]
        created: list[AlertRead] = []
        for crop in targets:
            crop_name = crop.get("crop_name") if crop else None
            crop_id = UUID(crop["id"]) if crop else None
            attach_symptoms = bool(request.symptoms) and (
                crop_id == request.crop_id
                or (request.crop_id is None and (not crops or len(crops) == 1))
            )
            drafts = detect_alerts(
                self.settings,
                crop_name=crop_name,
                current=current,
                forecast=forecast,
                soil_moisture=soil,
                symptoms=request.symptoms if attach_symptoms else None,
            )
            for draft in drafts:
                if self.records.find_recent_alert(
                    draft.category,
                    request.location_id,
                    crop_id,
                    self.settings.alert_dedupe_hours,
                ):
                    continue
                description = self._description(draft)
                row = self.records.create_alert(
                    {
                        "crop_id": str(crop_id) if crop_id else None,
                        "location_id": str(request.location_id),
                        "title": draft.title,
                        "description": description,
                        "category": draft.category,
                        "severity": draft.severity,
                        "supporting_context": draft.supporting_context,
                        "is_read": False,
                    }
                )
                created.append(AlertRead.model_validate(row))
        return created

    def _description(self, draft) -> str:
        if not self.llm.config.chat_configured:
            return draft.description
        try:
            raw = self.llm.complete_json(
                self.prompts.load("alert_explanation.txt"),
                draft.model_dump_json(),
            )
        except AppError:
            logger.info("Alert explanation was not generated. The rule text was kept.")
            return draft.description
        explanation = validate_alert_explanation(raw)
        if explanation is None:
            return draft.description
        action = explanation.suggested_action.strip()
        if action:
            return f"{explanation.description.strip()} Suggested action: {action}"
        return explanation.description.strip()
