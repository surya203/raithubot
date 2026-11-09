import json
import logging
import re
from typing import Any, Protocol

from pydantic import ValidationError

from app.errors import IntegrationError
from app.schemas.advisory import AdvisoryBody, EvidenceItem
from app.schemas.alerts import AlertExplanation
from app.schemas.chat import ChatAnswer

logger = logging.getLogger(__name__)

RATE_PATTERN = re.compile(
    r"("
    r"\b\d+(?:\.\d+)?\s*(?:kg|g|ml|l|litre|liter)s?\s*/\s*(?:ha|hectare|acre)\b"
    r"|"
    r"\bspray\b[^.]*\b\d+(?:\.\d+)?\s*(?:ml|g|kg)\b"
    r")",
    re.IGNORECASE,
)

NO_KNOWLEDGE = "No agricultural knowledge document was retrieved for this request."
REMOVED_CITATION = "A citation that was not in the retrieved documents was removed."
REMOVED_RATE = (
    "A recommendation with a specific application rate was removed. "
    "This system does not prescribe fertilizer or chemical quantities."
)
DISEASE_LIMIT = (
    "This is not a confirmed disease diagnosis and it is not a pesticide prescription. "
    "Follow locally approved agricultural guidance."
)


class CitedChunk(Protocol):
    title: str
    content: str
    source_organization: str | None
    document_url: str | None


def parse_json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, count=1, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise IntegrationError("The language model did not return JSON.")
    try:
        value = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise IntegrationError("The language model returned invalid JSON.") from exc
    if not isinstance(value, dict):
        raise IntegrationError("The language model did not return a JSON object.")
    return value


def validate_advisory(
    raw: str,
    *,
    crop_name: str,
    growth_stage: str,
    advisory_type: str,
    symptoms: str,
    retrieved: list[CitedChunk],
) -> AdvisoryBody:
    data = prepare_advisory_payload(parse_json_object(raw))
    try:
        body = AdvisoryBody.model_validate(data)
    except ValidationError as exc:
        logger.warning("Advisory schema mismatch: %s", _validation_summary(exc))
        raise IntegrationError(
            "The language model response did not match the advisory schema."
        ) from exc

    body.crop = crop_name
    body.growth_stage = growth_stage
    body.advisory_type = advisory_type
    limitations = list(body.limitations)
    body.evidence = ground_evidence(body.evidence, retrieved, limitations)
    body.recommendations, removed = strip_rates(body.recommendations)
    if removed:
        _append(limitations, REMOVED_RATE)
    if not retrieved:
        body.evidence = []
        _append(limitations, NO_KNOWLEDGE)
    if advisory_type == "disease_prevention":
        body.disease_status = _disease_status(body.disease_status, symptoms)
        _append(limitations, DISEASE_LIMIT)
    else:
        body.disease_status = None
    body.limitations = limitations
    body.observations = _strings(body.observations)
    body.possible_concerns = _strings(body.possible_concerns)
    body.missing_information = _strings(body.missing_information)
    return body


def validate_chat(raw: str, retrieved: list[CitedChunk]) -> ChatAnswer:
    data = prepare_chat_payload(parse_json_object(raw))
    try:
        answer = ChatAnswer.model_validate(data)
    except ValidationError as exc:
        logger.warning("Chat schema mismatch: %s", _validation_summary(exc))
        raise IntegrationError(
            "The language model response did not match the chat schema."
        ) from exc
    if not answer.answer.strip():
        raise IntegrationError("The language model returned an empty answer.")
    limitations = list(answer.limitations)
    answer.references = ground_evidence(answer.references, retrieved, limitations)
    if not retrieved:
        answer.references = []
        _append(limitations, NO_KNOWLEDGE)
    answer.limitations = limitations
    answer.missing_information = _strings(answer.missing_information)
    return answer


def validate_alert_explanation(raw: str) -> AlertExplanation | None:
    try:
        data = parse_json_object(raw)
        explanation = AlertExplanation.model_validate(data)
    except (IntegrationError, ValidationError):
        return None
    if not explanation.description.strip():
        return None
    return explanation


def ground_evidence(
    items: list[EvidenceItem],
    retrieved: list[CitedChunk],
    limitations: list[str],
) -> list[EvidenceItem]:
    by_title = {chunk.title.strip().casefold(): chunk for chunk in retrieved if chunk.title}
    kept: list[EvidenceItem] = []
    dropped = False
    for item in items:
        chunk = by_title.get(item.title.strip().casefold())
        if chunk is None:
            dropped = True
            continue
        excerpt = (item.excerpt or "").strip()
        if not excerpt or _compact(excerpt) not in _compact(chunk.content):
            excerpt = chunk.content[:240].strip()
        kept.append(
            EvidenceItem(
                title=chunk.title,
                source_organization=chunk.source_organization,
                document_url=chunk.document_url,
                excerpt=excerpt or None,
            )
        )
    if dropped:
        _append(limitations, REMOVED_CITATION)
    return kept


def strip_rates(recommendations: list[str]) -> tuple[list[str], bool]:
    kept: list[str] = []
    removed = False
    for item in recommendations:
        text = item.strip()
        if not text:
            continue
        if RATE_PATTERN.search(text):
            removed = True
            continue
        kept.append(text)
    return kept, removed


LIST_FIELDS = (
    "observations",
    "possible_concerns",
    "recommendations",
    "missing_information",
    "limitations",
)
TEXT_KEYS = (
    "text",
    "recommendation",
    "action",
    "observation",
    "concern",
    "description",
    "value",
    "content",
    "message",
)
RISK_ALIASES = {
    "low": "low",
    "medium": "moderate",
    "moderate": "moderate",
    "med": "moderate",
    "high": "high",
    "severe": "high",
    "insufficient": "insufficient_evidence",
    "insufficient_evidence": "insufficient_evidence",
    "unknown": "insufficient_evidence",
    "uncertain": "insufficient_evidence",
    "none": "insufficient_evidence",
}
DISEASE_ALIASES = {
    "environmental_risk": "environmental_risk",
    "environmental": "environmental_risk",
    "weather_risk": "environmental_risk",
    "suspected_from_symptoms": "suspected_from_symptoms",
    "suspected": "suspected_from_symptoms",
    "symptom_based": "suspected_from_symptoms",
    "not_assessed": "not_assessed",
    "not_assessed_yet": "not_assessed",
    "unknown": "not_assessed",
    "none": "not_assessed",
    "not_confirmed": "not_assessed",
}


def prepare_chat_payload(data: dict) -> dict:
    """Accept reply shapes models use instead of the chat object."""
    data = _unwrap_chat(data)
    references = data.get("references")
    if references is None:
        references = data.get("evidence") or data.get("citations") or data.get("sources")
    return {
        "answer": _chat_answer(data),
        "references": _evidence_list(references),
        "missing_information": _string_list(data.get("missing_information")),
        "limitations": _string_list(data.get("limitations")),
    }


def prepare_advisory_payload(data: dict) -> dict:
    """Accept the field shapes models commonly return, then let the schema check the rest."""
    data = _unwrap_advisory(data)
    if not isinstance(data.get("crop"), str) or not data["crop"].strip():
        data["crop"] = str(data.get("crop_name") or "crop")
    if not isinstance(data.get("advisory_type"), str) or not str(data.get("advisory_type")).strip():
        data["advisory_type"] = "advisory"
    if not isinstance(data.get("growth_stage"), str):
        data["growth_stage"] = None
    data["risk_level"] = _risk_level(data.get("risk_level"))
    if data.get("disease_status") is not None:
        data["disease_status"] = _disease_alias(data.get("disease_status"))
    for field in LIST_FIELDS:
        data[field] = _string_list(data.get(field))
    data["evidence"] = _evidence_list(data.get("evidence"))
    return data


def _unwrap_chat(data: dict) -> dict:
    if any(key in data for key in ("answer", "message", "reply")):
        return data
    for key in ("response", "chat", "result", "data"):
        nested = data.get(key)
        if isinstance(nested, dict):
            return nested
        if isinstance(nested, str) and nested.strip():
            return {"answer": nested}
    return data


def _chat_answer(data: dict) -> str:
    for key in ("answer", "message", "reply", "response", "text", "content"):
        text = _as_prose(data.get(key))
        if text:
            return text
    lines = []
    for key in ("observations", "possible_concerns", "recommendations"):
        lines.extend(_string_list(data.get(key)))
    return "\n".join(lines)


def _as_prose(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(line for line in (_text_item(item) for item in value) if line)
    if isinstance(value, dict):
        return _text_item(value)
    return ""


def _unwrap_advisory(data: dict) -> dict:
    if "risk_level" in data or "recommendations" in data:
        return data
    for key in ("advisory", "response", "result", "data"):
        nested = data.get(key)
        if isinstance(nested, dict) and ("risk_level" in nested or "recommendations" in nested):
            return dict(nested)
    return data


def _risk_level(value: Any) -> str:
    token = _token(value)
    if token in RISK_ALIASES:
        return RISK_ALIASES[token]
    if "insufficient" in token or "unknown" in token:
        return "insufficient_evidence"
    if "high" in token or "severe" in token:
        return "high"
    if "medium" in token or "moderat" in token:
        return "moderate"
    if token == "low":
        return "low"
    return "insufficient_evidence"


def _disease_alias(value: Any) -> str | None:
    token = _token(value)
    if not token:
        return None
    if token in DISEASE_ALIASES:
        return DISEASE_ALIASES[token]
    if "symptom" in token or "suspect" in token:
        return "suspected_from_symptoms"
    if "environment" in token or "weather" in token:
        return "environmental_risk"
    return "not_assessed"


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, dict):
        value = list(value.values())
    if not isinstance(value, list):
        text = str(value).strip()
        return [text] if text else []
    items: list[str] = []
    for item in value:
        text = _text_item(item)
        if text:
            items.append(text)
    return items


def _evidence_list(value: Any) -> list[dict]:
    if value is None:
        return []
    if isinstance(value, dict):
        value = [value]
    if isinstance(value, str):
        text = value.strip()
        return [{"title": text}] if text else []
    if not isinstance(value, list):
        return []
    items: list[dict] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            items.append({"title": item.strip()})
            continue
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("source") or item.get("name") or item.get("document")
        if not isinstance(title, str) or not title.strip():
            continue
        excerpt = item.get("excerpt")
        items.append(
            {
                "title": title.strip(),
                "source_organization": _optional_str(item.get("source_organization")),
                "document_url": _optional_str(item.get("document_url") or item.get("url")),
                "excerpt": None if excerpt is None else str(excerpt),
            }
        )
    return items


def _text_item(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in TEXT_KEYS:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""
    if item is None:
        return ""
    return str(item).strip()


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s\-]+", "_", value.strip().casefold())


def _validation_summary(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors():
        location = ".".join(str(item) for item in error.get("loc", ()))
        parts.append(f"{location}: {error.get('type')}")
    return "; ".join(parts) or "unknown"


def _disease_status(status: str | None, symptoms: str) -> str:
    has_symptoms = bool(symptoms.strip())
    if has_symptoms:
        if status == "suspected_from_symptoms":
            return status
        if status == "environmental_risk":
            return status
        return "suspected_from_symptoms"
    if status in {"environmental_risk", "not_assessed"}:
        return status
    return "environmental_risk"


def _strings(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value and value.strip()]


def _append(values: list[str], note: str) -> None:
    if note not in values:
        values.append(note)


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).casefold()
