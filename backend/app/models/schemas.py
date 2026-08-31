from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

FACT_NAMES = [
    "product_name",
    "ingredients_text",
    "ingredients_list",
    "allergen_statement",
    "emphasised_allergens",
    "nutrition_panel",
    "net_quantity",
    "retail_sale_price",
    "consumer_care_details",
    "batch_or_lot",
    "manufacture_or_packaging_date",
    "expiry_or_use_by_date",
    "best_before_date",
    "use_by_date",
    "business_name_address",
    "importer_name_address",
    "country_of_origin",
    "fssai_licence_number",
    "veg_nonveg_symbol",
    "warnings",
    "storage_instructions",
    "usage_instructions",
    "min_text_height_mm",
    "declared_panel_area_cm2",
    "largest_surface_area_cm2",
]


class Jurisdiction(str, Enum):
    india = "IN"
    uk = "UK"


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Status(str, Enum):
    passed = "PASS"
    failed = "FAIL"
    needs_review = "NEEDS_REVIEW"
    not_applicable = "NOT_APPLICABLE"


class Verdict(str, Enum):
    confirmed = "confirmed"
    rejected = "rejected"
    uncertain = "uncertain"


class Evidence(BaseModel):
    kind: Literal["ocr_text", "vision_observation", "fact", "rule_text", "absence"]
    locator: str
    snippet: str = ""


class ExtractedField(BaseModel):
    present: bool
    value: Any = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = []
    extractor: Literal["ocr", "vision", "hybrid", "user_input"] = "hybrid"


class ProductContext(BaseModel):
    jurisdiction: Jurisdiction
    product_category: Literal["packaged_food"] = "packaged_food"
    imported: bool | None = None
    single_ingredient: bool | None = None
    pack_largest_surface_cm2: float | None = None
    principal_panel_area_cm2: float | None = None
    notes: str | None = None


class LabelFacts(BaseModel):
    raw_text: str = ""
    fields: dict[str, ExtractedField] = {}
    extraction_warnings: list[str] = []
    image_ref: str | None = None

    def get(self, name: str) -> ExtractedField | None:
        return self.fields.get(name)


class ApplicabilitySignals(BaseModel):
    single_ingredient_food: bool | None = None
    imported_product: bool | None = None
    contains_listed_allergen: bool | None = None
    date_marking_exempt_category: bool | None = None
    needs_storage_or_use_instructions: bool | None = None
    origin_declaration_required: bool | None = None
    nutrition_declaration_exempt: bool | None = None
    schedule_two_trigger: list[str] = []
    warning_trigger: list[str] = []


class RuleApplicabilityCondition(BaseModel):
    fact: str
    operator: Literal["is_true", "is_present", "equals", "in"]
    value: Any = None


class RuleApplicability(BaseModel):
    summary: str
    always_applies: bool
    conditions: list[RuleApplicabilityCondition] = []


class Rule(BaseModel):
    rule_id: str
    jurisdiction: Jurisdiction
    category: str
    requirement: str
    severity: Severity
    source_id: str
    source_reference: str
    source_excerpt: str
    applicability: RuleApplicability
    validation_type: Literal["text", "vision", "hybrid"]
    required_facts: list[str]
    evidence_hint: str = ""
    suggested_fix: str = ""
    needs_professional_review: bool = False
    notes: str = ""


class RuleSource(BaseModel):
    source_id: str
    name: str
    publisher: str = ""
    url: str
    retrieved_on: str | None = None


class RulePack(BaseModel):
    jurisdiction: Jurisdiction
    jurisdiction_name: str
    product_category: str
    pack_version: str
    retrieved_on: str | None = None
    scope_note: str = ""
    sources: list[RuleSource]
    rules: list[Rule]


class SelectedRule(BaseModel):
    rule: Rule
    applicable: bool
    applicability_reason: str


class CandidateFinding(BaseModel):
    finding_id: str
    rule_id: str
    status: Status
    severity: Severity
    explanation: str
    evidence: list[Evidence] = []
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_fix: str = ""


class VerificationResult(BaseModel):
    finding_id: str
    verdict: Verdict
    reason: str
    evidence: list[Evidence] = []
    revised_status: Status | None = None
    revised_confidence: float | None = None


class Finding(BaseModel):
    finding_id: str
    rule_id: str
    rule_reference: str
    requirement: str
    status: Status
    severity: Severity
    explanation: str
    evidence: list[Evidence] = []
    confidence: float
    suggested_fix: str = ""
    verification: VerificationResult | None = None
    source_name: str = ""
    source_url: str = ""


class ReportSummary(BaseModel):
    passed: int
    failed: int
    needs_review: int
    not_applicable: int
    critical_failures: int
    compliance_score: float


class ComplianceReport(BaseModel):
    report_id: str
    generated_at: datetime
    system: Literal["baseline", "agent"]
    product_name: str | None
    jurisdiction: Jurisdiction
    jurisdiction_name: str
    product_category: str
    overall_status: Literal["PASS", "FAIL", "NEEDS_REVIEW"]
    summary: ReportSummary
    findings: list[Finding]
    sources: list[RuleSource]
    disclaimer: str
    runtime_seconds: float | None = None
    token_usage: dict[str, int] = {}


class TraceEvent(BaseModel):
    timestamp: datetime
    agent: str
    step: str
    input_reference: str = ""
    tool_used: str = ""
    result: str = ""
    decision: str = ""
    duration_ms: int | None = None


class AnalysisTrace(BaseModel):
    case_id: str | None = None
    system: Literal["baseline", "agent"]
    events: list[TraceEvent] = []
