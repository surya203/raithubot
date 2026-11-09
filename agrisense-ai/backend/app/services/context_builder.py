import json
from typing import Any

from app.schemas.knowledge import RetrievedChunk
from app.schemas.weather import CurrentWeather, ForecastWeather


def build_context(
    *,
    crop: dict | None,
    location: dict | None,
    current: CurrentWeather | None,
    forecast: ForecastWeather | None,
    chunks: list[RetrievedChunk],
    symptoms: str | None = None,
    weather_error: str | None = None,
    retrieval_note: str | None = None,
    recent_advisories: list[dict] | None = None,
    conversation: list[dict] | None = None,
    question: str | None = None,
) -> dict[str, Any]:
    return {
        "question": question,
        "crop": _crop(crop),
        "location": _location(location),
        "weather": _dump(current),
        "forecast": _dump(forecast),
        "weather_error": weather_error,
        "symptoms": (symptoms or "").strip(),
        "retrieved_knowledge": [_chunk(chunk) for chunk in chunks],
        "retrieval_note": retrieval_note,
        "recent_advisories": [_advisory(row) for row in (recent_advisories or [])],
        "recent_conversation": conversation or [],
        "note": "Null measurements are unavailable. Do not invent replacements.",
    }


def context_text(context: dict) -> str:
    return json.dumps(context, ensure_ascii=False, default=str)


def source_snapshot(chunks: list[RetrievedChunk]) -> list[dict]:
    return [
        {
            "document_id": str(chunk.document_id),
            "title": chunk.title,
            "source_organization": chunk.source_organization,
            "document_url": chunk.document_url,
            "excerpt": chunk.content[:400],
            "cosine_similarity": chunk.similarity,
        }
        for chunk in chunks
    ]


def _dump(model: CurrentWeather | ForecastWeather | None) -> dict | None:
    if model is None:
        return None
    return model.model_dump(mode="json")


def _crop(row: dict | None) -> dict | None:
    if row is None:
        return None
    keys = [
        "crop_name",
        "variety",
        "sowing_date",
        "expected_harvest_date",
        "growth_stage",
        "soil_type",
        "soil_ph",
        "nitrogen",
        "phosphorus",
        "potassium",
        "irrigation_method",
        "observations",
    ]
    return {key: row.get(key) for key in keys}


def _location(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {
        "name": row.get("name"),
        "state": row.get("state"),
        "district": row.get("district"),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
    }


def _chunk(chunk: RetrievedChunk) -> dict:
    return {
        "title": chunk.title,
        "source_organization": chunk.source_organization,
        "document_url": chunk.document_url,
        "excerpt": chunk.content[:1200],
    }


def _advisory(row: dict) -> dict:
    response = row.get("advisory_response") or {}
    recommendations = response.get("recommendations") or []
    return {
        "advisory_type": row.get("advisory_type"),
        "created_at": row.get("created_at"),
        "risk_level": response.get("risk_level"),
        "recommendations": recommendations[:3] if isinstance(recommendations, list) else [],
    }
