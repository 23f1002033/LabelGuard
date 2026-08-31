import pytest
from app.agents.extraction_agent import EXTRACTABLE_FACTS, run_extraction
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
