import logging
from uuid import UUID, uuid4

from app.errors import AppError
from app.repositories.records import RecordsRepository
from app.schemas.chat import ChatAnswer, ChatMessageRead, ChatRequest, ChatResponse
from app.services.context_builder import build_context, context_text, source_snapshot
from app.services.llm_service import LLMService
from app.services.prompt_manager import PromptManager
from app.services.rag_service import RAGService
from app.services.response_validator import validate_chat
from app.services.weather_service import WeatherService

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        records: RecordsRepository,
        weather: WeatherService,
        rag: RAGService,
        llm: LLMService,
        prompts: PromptManager,
    ) -> None:
        self.records = records
        self.weather = weather
        self.rag = rag
        self.llm = llm
        self.prompts = prompts

    def history(self, conversation_id: UUID) -> list[ChatMessageRead]:
        return [
            ChatMessageRead.model_validate(row)
            for row in self.records.list_chat(conversation_id)
        ]

    def reply(self, request: ChatRequest) -> ChatResponse:
        conversation_id = request.conversation_id or uuid4()
        crop = None
        location = None
        if request.crop_id is not None:
            crop = self.records.get_crop(request.crop_id)
            location = self.records.get_location(UUID(crop["location_id"]))
        current, forecast, weather_error = self._weather(location)
        prior = self.history(conversation_id)[-8:]
        chunks, retrieval_note = self._retrieve(request.message, crop)
        context = build_context(
            crop=crop,
            location=location,
            current=current,
            forecast=forecast,
            chunks=chunks,
            weather_error=weather_error,
            retrieval_note=retrieval_note,
            recent_advisories=self.records.recent_advisories(request.crop_id) if request.crop_id else [],
            conversation=[
                {"role": item.role, "message": item.message}
                for item in prior
            ],
            question=request.message,
        )
        answer = self._complete(context, chunks)
        if weather_error and weather_error not in answer.missing_information:
            answer.missing_information.append(f"Live weather was unavailable: {weather_error}")
        self._save(conversation_id, request.crop_id, "user", request.message, {})
        saved = self._save(
            conversation_id,
            request.crop_id,
            "assistant",
            answer.answer,
            {"references": [item.model_dump(mode="json") for item in answer.references]},
        )
        self._record_advisory(request.crop_id, location, context, answer, chunks)
        return ChatResponse(conversation_id=conversation_id, message=saved, answer=answer)

    def _record_advisory(self, crop_id, location, context, answer, chunks) -> None:
        try:
            self.records.create_advisory(
                {
                    "crop_id": str(crop_id) if crop_id else None,
                    "location_id": str(location["id"]) if location else None,
                    "advisory_type": "chatbot",
                    "input_context": context,
                    "advisory_response": answer.model_dump(mode="json"),
                    "retrieved_sources": source_snapshot(chunks),
                }
            )
        except AppError:
            logger.info("Chat reply was not copied into advisory history.")

    def _weather(self, location: dict | None):
        if location is None:
            return None, None, None
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

    def _retrieve(self, message: str, crop: dict | None):
        try:
            chunks = self.rag.retrieve(message, crop=crop.get("crop_name") if crop else None)
            return chunks, None
        except AppError as exc:
            return [], exc.message

    def _complete(self, context: dict, chunks) -> ChatAnswer:
        system = self.prompts.load("chatbot.txt")
        user = context_text(context)
        raw = self.llm.complete_json(system, user)
        try:
            return validate_chat(raw, chunks)
        except AppError as exc:
            logger.warning("Chat response was repaired after: %s", exc.message)
            repaired = self.llm.complete_json(
                system,
                user
                + "\n\nThe previous response was invalid. Return only one JSON object "
                "with an answer string. references must be an array of objects that each "
                "have a title string. missing_information and limitations must be arrays of strings.",
            )
            return validate_chat(repaired, chunks)

    def _save(
        self,
        conversation_id: UUID,
        crop_id: UUID | None,
        role: str,
        message: str,
        metadata: dict,
    ) -> ChatMessageRead:
        row = self.records.add_chat_message(
            {
                "conversation_id": str(conversation_id),
                "crop_id": str(crop_id) if crop_id else None,
                "role": role,
                "message": message,
                "metadata": metadata,
            }
        )
        return ChatMessageRead.model_validate(row)
