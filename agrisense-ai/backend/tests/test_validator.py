import pytest

from app.errors import IntegrationError
from app.services.response_validator import validate_advisory, validate_chat


class Chunk:
    def __init__(self) -> None:
        self.title = "Rice field guide"
        self.content = "Inspect the canopy after several humid nights and improve drainage."
        self.source_organization = "ICAR"
        self.document_url = "https://icar.example/rice"


def test_unknown_citation_and_application_rate_are_removed():
    raw = """
    {
      "crop": "Wrong",
      "growth_stage": "Wrong",
      "advisory_type": "crop_management",
      "risk_level": "Moderate",
      "observations": ["Humidity is high."],
      "possible_concerns": [],
      "recommendations": [
        "Inspect leaves in the morning.",
        "Apply 50 kg/ha urea tomorrow."
      ],
      "evidence": [
        {"title": "Invented bulletin", "excerpt": "This was not retrieved."},
        {"title": "Rice field guide", "excerpt": "not in the source"}
      ],
      "missing_information": [],
      "limitations": []
    }
    """
    body = validate_advisory(
        raw,
        crop_name="Paddy",
        growth_stage="vegetative",
        advisory_type="crop_management",
        symptoms="",
        retrieved=[Chunk()],
    )
    assert body.crop == "Paddy"
    assert body.growth_stage == "vegetative"
    assert body.risk_level == "moderate"
    assert body.recommendations == ["Inspect leaves in the morning."]
    assert len(body.evidence) == 1
    assert body.evidence[0].source_organization == "ICAR"
    assert "Inspect the canopy" in body.evidence[0].excerpt
    assert any("citation" in item.lower() for item in body.limitations)
    assert any("application rate" in item.lower() for item in body.limitations)


def test_symptoms_are_not_treated_as_a_confirmed_diagnosis():
    raw = """
    {
      "crop": "Tomato",
      "growth_stage": "flowering",
      "advisory_type": "disease_prevention",
      "risk_level": "insufficient_evidence",
      "disease_status": "not_assessed",
      "observations": [],
      "possible_concerns": ["Leaf spots are a hypothesis only."],
      "recommendations": ["Scout the field."],
      "evidence": [],
      "missing_information": ["Variety is unknown."],
      "limitations": []
    }
    """
    body = validate_advisory(
        raw,
        crop_name="Tomato",
        growth_stage="flowering",
        advisory_type="disease_prevention",
        symptoms="Brown spots on lower leaves",
        retrieved=[],
    )
    assert body.disease_status == "suspected_from_symptoms"
    assert body.evidence == []
    assert any("not a confirmed" in item.lower() for item in body.limitations)
    assert any("no agricultural knowledge" in item.lower() for item in body.limitations)


def test_loose_model_shapes_are_accepted():
    raw = """
    {
      "advisory": {
        "risk_level": "medium",
        "disease_status": "suspected",
        "observations": "Humidity stayed high overnight.",
        "recommendations": [{"action": "Scout the lower leaves in the morning."}],
        "evidence": ["Rice field guide"],
        "possible_concerns": [],
        "missing_information": [],
        "limitations": []
      }
    }
    """
    body = validate_advisory(
        raw,
        crop_name="Paddy",
        growth_stage="vegetative",
        advisory_type="disease_prevention",
        symptoms="Yellowing on older leaves",
        retrieved=[Chunk()],
    )
    assert body.crop == "Paddy"
    assert body.risk_level == "moderate"
    assert body.disease_status == "suspected_from_symptoms"
    assert body.observations == ["Humidity stayed high overnight."]
    assert body.recommendations == ["Scout the lower leaves in the morning."]
    assert body.evidence[0].title == "Rice field guide"
    assert body.evidence[0].source_organization == "ICAR"


def test_invalid_advisory_json_is_rejected():
    with pytest.raises(IntegrationError):
        validate_advisory(
            "not json",
            crop_name="Paddy",
            growth_stage="vegetative",
            advisory_type="crop_management",
            symptoms="",
            retrieved=[],
        )


def test_chat_accepts_a_reply_that_uses_advisory_fields():
    raw = """
    {
      "response": {
        "recommendations": [{"action": "Scout the lower canopy after humid nights."}],
        "evidence": ["Rice field guide"],
        "limitations": "Weather alone does not confirm a disease."
      }
    }
    """
    answer = validate_chat(raw, [Chunk()])
    assert "Scout the lower canopy" in answer.answer
    assert answer.references[0].title == "Rice field guide"
    assert answer.references[0].source_organization == "ICAR"
    assert answer.limitations[0] == "Weather alone does not confirm a disease."


def test_chat_references_must_come_from_retrieved_chunks():
    raw = """
    {
      "answer": "Scout after humid weather and do not treat this as a diagnosis.",
      "references": [{"title": "Made up source", "excerpt": "invented"}],
      "missing_information": [],
      "limitations": []
    }
    """
    answer = validate_chat(raw, [Chunk()])
    assert answer.references == []
    assert any("citation" in item.lower() for item in answer.limitations)
