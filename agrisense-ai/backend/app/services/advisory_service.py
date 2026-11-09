import logging
from uuid import UUID

from app.errors import AppError
from app.repositories.records import RecordsRepository
from app.schemas.advisory import AdvisoryBody, AdvisoryRead
from app.schemas.alerts import AlertEvaluateRequest
from app.services.alert_service import AlertService
from app.services.catalog_service import EnvironmentService
from app.services.context_builder import build_context, context_text, source_snapshot
from app.services.llm_service import LLMService
from app.services.prompt_manager import PromptManager
from app.services.rag_service import RAGService
from app.services.response_validator import validate_advisory
from app.services.weather_service import WeatherService

logger = logging.getLogger(__name__)

PROMPTS = {
    "crop_management": "crop_advisory.txt",
    "disease_prevention": "disease_advisory.txt",
}


class AdvisoryService:
    def __init__(
        self,
        records: RecordsRepository,
        weather: WeatherService,
        environment: EnvironmentService,
        rag: RAGService,
        llm: LLMService,
        prompts: PromptManager,
        alerts: AlertService,
    ) -> None:
        self.records = records
        self.weather = weather
        self.environment = environment
        self.rag = rag
        self.llm = llm
        self.prompts = prompts
        self.alerts = alerts

    def crop_advisory(self, crop_id: UUID) -> AdvisoryRead:
        return self._generate(crop_id, "crop_management", "")

    def disease_advisory(self, crop_id: UUID, symptoms: str) -> AdvisoryRead:
        return self._generate(crop_id, "disease_prevention", symptoms.strip())

    def history(
        self,
        crop_id: UUID | None = None,
        advisory_type: str | None = None,
        date_from=None,
        date_to=None,
        limit: int = 50,
    ) -> list[AdvisoryRead]:
        rows = self.records.list_advisories(crop_id, advisory_type, date_from, date_to, limit)
        return [AdvisoryRead.model_validate(row) for row in rows]

    def get(self, advisory_id: UUID) -> AdvisoryRead:
        return AdvisoryRead.model_validate(self.records.get_advisory(advisory_id))

    def _generate(self, crop_id: UUID, advisory_type: str, symptoms: str) -> AdvisoryRead:
        crop = self.records.get_crop(crop_id)
        location = self.records.get_location(UUID(crop["location_id"]))
        current, forecast, weather_error = self._weather(location)
        if current is not None and not current.from_cache:
            try:
                self.environment.store_weather(UUID(location["id"]), crop_id, current)
            except AppError:
                logger.info("Weather snapshot was not stored for advisory %s", crop_id)
        chunks, retrieval_note = self._retrieve(crop, symptoms, advisory_type)
        context = build_context(
            crop=crop,
            location=location,
            current=current,
            forecast=forecast,
            chunks=chunks,
            symptoms=symptoms,
            weather_error=weather_error,
            retrieval_note=retrieval_note,
            recent_advisories=self.records.recent_advisories(crop_id),
        )
        body = self._complete(advisory_type, context, crop, symptoms, chunks)
        if weather_error:
            note = f"Live weather was unavailable: {weather_error}"
            if note not in body.missing_information:
                body.missing_information.append(note)
        row = self.records.create_advisory(
            {
                "crop_id": str(crop_id),
                "location_id": str(location["id"]),
                "advisory_type": advisory_type,
                "input_context": context,
                "advisory_response": body.model_dump(mode="json"),
                "retrieved_sources": source_snapshot(chunks),
            }
        )
        self._evaluate_alerts(location, crop_id, symptoms, current, forecast)
        return AdvisoryRead.model_validate(row)

    def _weather(self, location: dict):
        try:
            latitude = float(location["latitude"])
            longitude = float(location["longitude"])
            return (
                self.weather.current(latitude, longitude),
                self.weather.forecast(latitude, longitude),
                None,
            )
        except AppError as exc:
            return None, None, exc.message

    def _retrieve(self, crop: dict, symptoms: str, advisory_type: str):
        query = " ".join(
            part
            for part in [
                crop.get("crop_name"),
                crop.get("growth_stage"),
                "disease prevention" if advisory_type == "disease_prevention" else "crop management",
                symptoms,
            ]
            if part
        )
        try:
            chunks = self.rag.retrieve(
                query,
                crop=crop.get("crop_name"),
                disease=None,
            )
            return chunks, None
        except AppError as exc:
            return [], exc.message

    def _complete(self, advisory_type: str, context: dict, crop: dict, symptoms: str, chunks) -> AdvisoryBody:
        system = self.prompts.load(PROMPTS[advisory_type])
        user = context_text(context)
        raw = self.llm.complete_json(system, user)
        try:
            return validate_advisory(
                raw,
                crop_name=crop["crop_name"],
                growth_stage=crop["growth_stage"],
                advisory_type=advisory_type,
                symptoms=symptoms,
                retrieved=chunks,
            )
        except AppError as exc:
            logger.warning("Advisory response was repaired after: %s", exc.message)
            repaired = self.llm.complete_json(
                system,
                user
                + "\n\nThe previous response was invalid. Return only one JSON object. "
                "risk_level must be low, moderate, high, or insufficient_evidence. "
                "observations, possible_concerns, recommendations, missing_information, "
                "and limitations must be arrays of strings. "
                "evidence must be an array of objects that each have a title string.",
            )
            return validate_advisory(
                repaired,
                crop_name=crop["crop_name"],
                growth_stage=crop["growth_stage"],
                advisory_type=advisory_type,
                symptoms=symptoms,
                retrieved=chunks,
            )

    def _evaluate_alerts(self, location, crop_id, symptoms, current, forecast) -> None:
        try:
            self.alerts.evaluate(
                AlertEvaluateRequest(
                    location_id=UUID(location["id"]),
                    crop_id=crop_id,
                    symptoms=symptoms or None,
                ),
                current=current,
                forecast=forecast,
                fetch_weather=False,
            )
        except AppError:
            logger.info("Alerts were not created for advisory %s", crop_id)
