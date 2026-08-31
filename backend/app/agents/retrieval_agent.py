from __future__ import annotations

from app.models.schemas import (
    ApplicabilitySignals,
    LabelFacts,
    ProductContext,
    Rule,
    RuleApplicabilityCondition,
    RulePack,
    SelectedRule,
)

ALLERGEN_KEYWORDS: dict[str, list[str]] = {
    "cereals containing gluten": ["wheat", "rye", "barley", "oats", "spelt", "gluten"],
    "crustaceans": ["prawn", "crab", "lobster", "shrimp", "crustacean"],
    "eggs": ["egg"],
    "fish": ["fish", "anchov", "tuna", "salmon", "sardine"],
    "peanuts": ["peanut", "groundnut"],
    "soybeans": ["soy", "soya"],
    "milk": ["milk", "dairy", "casein", "whey", "butter", "cream", "cheese", "ghee"],
    "tree nuts": ["almond", "cashew", "walnut", "pistachio", "hazelnut", "pecan", "macadamia", "brazil nut"],
    "sulphite": ["sulphite", "sulfite", "sulphur dioxide", "sulfur dioxide"],
    "celery": ["celery"],
    "mustard": ["mustard"],
    "sesame": ["sesame"],
    "lupin": ["lupin"],
    "molluscs": ["mussel", "squid", "oyster", "scallop", "snail", "mollusc"],
}

WARNING_TRIGGER_KEYWORDS: dict[str, list[str]] = {
    "caffeine": ["caffeine"],
    "polyols": ["polyol", "sorbitol", "mannitol", "xylitol", "maltitol", "isomalt"],
    "polydextrose": ["polydextrose"],
    "aspartame": ["aspartame"],
    "sweetener": ["sweetener", "sucralose", "acesulfame", "saccharin", "stevia"],
    "sulphite": ["sulphite", "sulfite", "sulphur dioxide", "sulfur dioxide"],
}

DATE_MARKING_EXEMPT_KEYWORDS = [
    "wine",
    "vinegar",
    "chewing gum",
    "bubble gum",
    "fresh fruit",
    "fresh vegetable",
    "solid sugar",
    "sugar boiled confectionery",
]


def _fact_text(facts: LabelFacts, *names: str) -> str:
    parts = []
    for name in names:
        field = facts.get(name)
        if field and field.present and field.value:
            if isinstance(field.value, list):
                parts.extend(str(v) for v in field.value)
            else:
                parts.append(str(field.value))
    return " ".join(parts).lower()


def _match_keywords(text: str, keyword_map: dict[str, list[str]]) -> list[str]:
    return [label for label, keywords in keyword_map.items() if any(k in text for k in keywords)]


def derive_signals(facts: LabelFacts, context: ProductContext) -> ApplicabilitySignals:
    ingredients_text = _fact_text(facts, "ingredients_text", "ingredients_list")
    name_text = _fact_text(facts, "product_name")

    single_ingredient = context.single_ingredient if context.single_ingredient is not None else False

    imported = context.imported
    if imported is None:
        country_present = bool(facts.get("country_of_origin") and facts.get("country_of_origin").present)
        importer_present = bool(facts.get("importer_name_address") and facts.get("importer_name_address").present)
        imported = country_present or importer_present

    contains_allergen = bool(_match_keywords(ingredients_text, ALLERGEN_KEYWORDS))
    date_exempt = any(kw in name_text or kw in ingredients_text for kw in DATE_MARKING_EXEMPT_KEYWORDS)
    warning_triggers = _match_keywords(ingredients_text, WARNING_TRIGGER_KEYWORDS)

    return ApplicabilitySignals(
        single_ingredient_food=single_ingredient,
        imported_product=imported,
        contains_listed_allergen=contains_allergen,
        date_marking_exempt_category=date_exempt,
        needs_storage_or_use_instructions=True,
        origin_declaration_required=bool(imported),
        nutrition_declaration_exempt=False,
        schedule_two_trigger=warning_triggers,
        warning_trigger=warning_triggers,
    )


def _condition_met(condition: RuleApplicabilityCondition, signals: ApplicabilitySignals) -> bool:
    value = getattr(signals, condition.fact, None)
    if condition.operator == "is_true":
        return bool(value)
    if condition.operator == "is_present":
        if isinstance(value, list):
            return len(value) > 0
        return bool(value)
    if condition.operator == "equals":
        return value == condition.value
    if condition.operator == "in":
        if isinstance(value, list):
            return condition.value in value
        return value in (condition.value or [])
    return False


def _rule_applicability(rule: Rule, signals: ApplicabilitySignals) -> tuple[bool, str]:
    if rule.applicability.always_applies:
        return True, "Always applies to pre-packaged food in this category."

    results = [_condition_met(c, signals) for c in rule.applicability.conditions]
    applicable = all(results) if results else True
    if applicable:
        return True, rule.applicability.summary
    detail = "; ".join(
        f"{c.fact}={getattr(signals, c.fact, None)!r} does not satisfy {c.operator} {c.value!r}"
        for c, met in zip(rule.applicability.conditions, results)
        if not met
    )
    return False, f"Not applicable: {rule.applicability.summary} ({detail})"


def select_rules(
    pack: RulePack, facts: LabelFacts, context: ProductContext
) -> tuple[list[SelectedRule], ApplicabilitySignals]:
    signals = derive_signals(facts, context)
    selected = []
    for rule in pack.rules:
        applicable, reason = _rule_applicability(rule, signals)
        selected.append(SelectedRule(rule=rule, applicable=applicable, applicability_reason=reason))
    return selected, signals
