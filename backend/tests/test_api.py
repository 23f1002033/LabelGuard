from pathlib import Path

import pytest
from app.config import settings
from app.main import app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_IMAGE = ROOT / "evaluation" / "images" / "IN-001.png"

client = TestClient(app)


@pytest.fixture(autouse=True)
def force_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "labelguard_mode", "mock")


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_jurisdictions_lists_india_and_uk():
    resp = client.get("/api/jurisdictions")
    assert resp.status_code == 200
    codes = {row["code"] for row in resp.json()}
    assert codes == {"IN", "UK"}
    for row in resp.json():
        assert row["rule_count"] > 0


def test_analyze_agent_happy_path():
    if not SAMPLE_IMAGE.exists():
        pytest.skip("run scripts/render_labels.py first to generate evaluation images")
    with open(SAMPLE_IMAGE, "rb") as f:
        resp = client.post(
            "/api/analyze",
            files={"image": ("label.png", f, "image/png")},
            data={"jurisdiction": "IN", "system": "agent"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["report"]["system"] == "agent"
    assert len(body["report"]["findings"]) == 13
    assert len(body["trace"]) == 6


def test_analyze_baseline_happy_path():
    if not SAMPLE_IMAGE.exists():
        pytest.skip("run scripts/render_labels.py first to generate evaluation images")
    with open(SAMPLE_IMAGE, "rb") as f:
        resp = client.post(
            "/api/analyze",
            files={"image": ("label.png", f, "image/png")},
            data={"jurisdiction": "UK", "system": "baseline"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["report"]["system"] == "baseline"
    assert len(body["report"]["findings"]) == 12


def test_analyze_rejects_unsupported_file_type():
    resp = client.post(
        "/api/analyze",
        files={"image": ("label.txt", b"not an image", "text/plain")},
        data={"jurisdiction": "IN"},
    )
    assert resp.status_code == 400


def test_analyze_rejects_corrupt_image_with_valid_mime_type():
    resp = client.post(
        "/api/analyze",
        files={"image": ("label.png", b"not actually a png", "image/png")},
        data={"jurisdiction": "IN"},
    )
    assert resp.status_code == 400


def test_analyze_rejects_unknown_system():
    if not SAMPLE_IMAGE.exists():
        pytest.skip("run scripts/render_labels.py first to generate evaluation images")
    with open(SAMPLE_IMAGE, "rb") as f:
        resp = client.post(
            "/api/analyze",
            files={"image": ("label.png", f, "image/png")},
            data={"jurisdiction": "IN", "system": "not-a-real-system"},
        )
    assert resp.status_code == 400


def test_analyze_requires_jurisdiction():
    resp = client.post(
        "/api/analyze",
        files={"image": ("label.png", b"placeholder", "image/png")},
    )
    assert resp.status_code == 422
