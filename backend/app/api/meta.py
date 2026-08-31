from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import Jurisdiction
from app.services import rules

router = APIRouter()


@router.get("/jurisdictions")
def list_jurisdictions():
    result = []
    for jurisdiction in Jurisdiction:
        pack = rules.load_rule_pack(jurisdiction)
        result.append(
            {
                "code": jurisdiction.value,
                "name": pack.jurisdiction_name,
                "product_category": pack.product_category,
                "rule_count": len(pack.rules),
                "scope_note": pack.scope_note,
            }
        )
    return result


@router.get("/health")
def health():
    return {"status": "ok"}
