import pytest
from app.agents.extraction_agent import (
    EXTRACTABLE_FACTS,
    _to_evidence,
    _to_extracted_field,
    run_extraction,
)
from app.config import settings


@pytest.fixture(autouse=True)
def force_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "labelguard_mode", "mock")


def test_mock_extraction_covers_every_extractable_fact():
    facts, usage = run_extraction(b"", "some ocr text")
    assert set(facts.fields.keys()) == set(EXTRACTABLE_FACTS)
    assert usage["total_tokens"] == 0


def test_mock_extraction_marks_everything_absent():
    facts, _usage = run_extraction(b"", "some ocr text")
    assert all(not field.present for field in facts.fields.values())


def test_extraction_preserves_raw_text():
    facts, _usage = run_extraction(b"", "Net Wt. 200 g")
    assert facts.raw_text == "Net Wt. 200 g"


def test_missing_field_from_model_response_normalizes_to_absent():
    field = _to_extracted_field("net_quantity", None)
    assert field.present is False
    assert field.value is None
    assert field.confidence == 0.0
    assert field.evidence == []


def test_confidence_is_clamped_to_zero_one_range():
    high = _to_extracted_field("net_quantity", {"present": True, "value": "200g", "confidence": 5.0})
    low = _to_extracted_field("net_quantity", {"present": True, "value": "200g", "confidence": -3.0})
    assert high.confidence == 1.0
    assert low.confidence == 0.0


def test_non_numeric_confidence_falls_back_to_midpoint():
    field = _to_extracted_field("net_quantity", {"present": True, "value": "200g", "confidence": "high"})
    assert field.confidence == 0.5


def test_ingredients_list_value_can_be_a_list():
    field = _to_extracted_field(
        "ingredients_list", {"present": True, "value": ["Sugar", "Salt"], "confidence": 0.9}
    )
    assert field.value == ["Sugar", "Salt"]


def test_empty_evidence_snippet_produces_no_evidence():
    assert _to_evidence("product_name", "") == []
    assert _to_evidence("product_name", "   ") == []


def test_ocr_text_facts_get_ocr_text_evidence_kind():
    evidence = _to_evidence("net_quantity", "Net Wt. 200 g")
    assert len(evidence) == 1
    assert evidence[0].kind == "ocr_text"


def test_vision_only_fact_gets_vision_observation_evidence_kind():
    evidence = _to_evidence("veg_nonveg_symbol", "green circle in a green square")
    assert len(evidence) == 1
    assert evidence[0].kind == "vision_observation"
