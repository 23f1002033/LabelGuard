from __future__ import annotations

from app.config import settings
from app.models.schemas import Evidence, ExtractedField, FACT_NAMES, LabelFacts
from app.services import llm_client

_PHYSICAL_ONLY_FACTS = {"min_text_height_mm", "declared_panel_area_cm2", "largest_surface_area_cm2"}

EXTRACTABLE_FACTS = [f for f in FACT_NAMES if f not in _PHYSICAL_ONLY_FACTS]

_FACT_DESCRIPTIONS = {
    "product_name": "the descriptive name of the food, not just a brand or trade name",
    "ingredients_text": "the full ingredients declaration as printed, verbatim",
    "ingredients_list": "the ingredients as a list of individual ingredient names, descending order as printed",
    "allergen_statement": "a separate allergen declaration distinct from the ingredients list, for example a 'Contains: ...' line",
    "emphasised_allergens": "allergen ingredient words that are visually distinguished from the rest of the ingredients list, for example bold, capitals, underline or a different colour or background; plain lowercase text does not count even if it names an allergen",
    "nutrition_panel": "a nutrition or nutritional information table or list, with energy and other nutrients per 100g/100ml or per serving",
    "net_quantity": "the net weight or volume of the food, for example Net Wt. 200 g or Net weight 300 g",
    "retail_sale_price": "a maximum retail price or selling price declaration",
    "consumer_care_details": "a customer care or consumer complaints contact, email or phone number",
    "batch_or_lot": "a batch, lot or code number identifying the production run",
    "manufacture_or_packaging_date": "the date of manufacture or packaging",
    "expiry_or_use_by_date": "an expiry date or a use by date",
    "best_before_date": "a best before date",
    "use_by_date": "a use by date, distinct from best before",
    "business_name_address": "the name AND a physical address (street, city, postcode or similar) of the manufacturer, packer, marketer or food business operator. A brand name, logo or product name on its own, with no physical address anywhere on the label, does NOT count as present, even if it looks like a company name.",
    "importer_name_address": "the name AND a physical address of the importer, only if this is an imported product. A brand name alone with no physical address does NOT count as present.",
    "country_of_origin": "an explicit country of origin statement",
    "fssai_licence_number": "an FSSAI licence number, usually a 14 digit number near an FSSAI logo",
    "veg_nonveg_symbol": "a vegetarian (green circle in a green square) or non-vegetarian (brown triangle in a brown square) symbol",
    "warnings": "any prescribed warning statement, for example about caffeine, sweeteners, polyols or allergens",
    "storage_instructions": "storage conditions, for example 'store in a cool dry place' or 'keep refrigerated'",
    "usage_instructions": "instructions for use, preparation or cooking",
}

_VISION_ONLY_FACTS = {"veg_nonveg_symbol"}


def _build_messages(ocr_text: str, image_data_url: str) -> list[dict]:
    fact_lines = "\n".join(f"- {name}: {desc}" for name, desc in _FACT_DESCRIPTIONS.items())
    system_prompt = (
        "You extract structured facts from a photo of a packaged food label. "
        "You are given the label image and the text an OCR engine extracted from it. "
        "For each of the following fields, decide whether it is present on the label. "
        "Never invent a value that is not actually visible or readable. If a field is "
        "not present, set present to false and leave value empty; do not guess. "
        f"Fields to extract:\n{fact_lines}\n\n"
        "Respond with a JSON object: {\"product_name_guess\": string or null, "
        '"fields": {"<field_name>": {"present": boolean, "value": string or list of '
        'strings or null, "confidence": number 0 to 1, "evidence_snippet": string}}}. '
        "Include every field name listed above as a key in fields, even when present "
        "is false. For ingredients_list use a JSON array of strings as the value. For "
        "emphasised_allergens use a JSON array of the specific allergen words that are "
        "visually emphasised, or an empty array if none are emphasised. Confidence "
        "should reflect how certain you are that the value is correct and complete, "
        "not just whether something was found."
    )
    user_text = "OCR extracted text from the label image:\n" + (ocr_text or "(no text extracted)")
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        },
    ]


def _to_evidence(field_name: str, snippet: str) -> list[Evidence]:
    snippet = (snippet or "").strip()
    if not snippet:
        return []
    kind = "vision_observation" if field_name in _VISION_ONLY_FACTS else "ocr_text"
    return [Evidence(kind=kind, locator="extraction_agent", snippet=snippet[:300])]


def _to_extracted_field(field_name: str, raw: dict | None) -> ExtractedField:
    if not raw:
        return ExtractedField(present=False, value=None, confidence=0.0, evidence=[], extractor="hybrid")
    present = bool(raw.get("present", False))
    value = raw.get("value")
    confidence = raw.get("confidence", 0.5)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.5
    return ExtractedField(
        present=present,
        value=value,
        confidence=confidence,
        evidence=_to_evidence(field_name, str(raw.get("evidence_snippet", ""))),
        extractor="hybrid",
    )


def _mock_facts(raw_text: str) -> LabelFacts:
    fields = {
        name: ExtractedField(present=False, value=None, confidence=0.0, evidence=[], extractor="hybrid")
        for name in EXTRACTABLE_FACTS
    }
    return LabelFacts(raw_text=raw_text, fields=fields, extraction_warnings=["mock mode: no live model call made"])


def run_extraction(image_bytes: bytes, raw_text: str, mime_type: str = "image/png") -> tuple[LabelFacts, dict]:
    if settings.mock_mode:
        return _mock_facts(raw_text), {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    image_data_url = llm_client.image_to_data_url(image_bytes, mime_type)
    messages = _build_messages(raw_text, image_data_url)
    parsed, usage = llm_client.chat_json(messages, model=settings.llm_vision_model)

    raw_fields = parsed.get("fields", {}) if isinstance(parsed, dict) else {}
    fields = {name: _to_extracted_field(name, raw_fields.get(name)) for name in EXTRACTABLE_FACTS}
    warnings = [name for name in EXTRACTABLE_FACTS if name not in raw_fields]

    facts = LabelFacts(raw_text=raw_text, fields=fields, extraction_warnings=warnings)
    return facts, usage
