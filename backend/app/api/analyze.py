from __future__ import annotations

import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from app.agents.baseline_agent import run_baseline
from app.agents.pipeline import run_agent
from app.config import settings
from app.models.schemas import ComplianceReport, Jurisdiction, ProductContext, TraceEvent

router = APIRouter()


class AnalyzeResponse(BaseModel):
    report: ComplianceReport
    trace: list[TraceEvent]


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    image: UploadFile = File(...),
    jurisdiction: Jurisdiction = Form(...),
    system: str = Form("agent"),
    imported: bool | None = Form(None),
    single_ingredient: bool | None = Form(None),
):
    if system not in ("agent", "baseline"):
        raise HTTPException(status_code=400, detail=f"Unknown system: {system}")

    if image.content_type not in settings.allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {image.content_type}")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(image_bytes) > settings.upload_max_bytes:
        raise HTTPException(status_code=400, detail="Image exceeds maximum upload size")

    try:
        Image.open(io.BytesIO(image_bytes)).verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image") from exc

    context = ProductContext(
        jurisdiction=jurisdiction,
        imported=imported,
        single_ingredient=single_ingredient,
    )
    mime_type = image.content_type or "image/png"

    if system == "baseline":
        compliance_report, trace = run_baseline(image_bytes, context, mime_type=mime_type)
    else:
        compliance_report, trace = run_agent(image_bytes, context, mime_type=mime_type)

    return AnalyzeResponse(report=compliance_report, trace=trace.trace.events)
