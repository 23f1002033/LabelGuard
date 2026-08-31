from app.agents import retrieval_agent
from app.models.schemas import ExtractedField, Jurisdiction, LabelFacts, ProductContext
from app.services import rules


def _facts(**field_values) -> LabelFacts:
    fields = {}
    for name, value in field_values.items():
        fields[name] = ExtractedField(present=True, value=value, confidence=0.9, evidence=[], extractor="hybrid")
    return LabelFacts(raw_text="", fields=fields)


def test_single_ingredient_defaults_false_when_context_unset():
    facts = _facts()
    context = ProductContext(jurisdiction=Jurisdiction.india)
    signals = retrieval_agent.derive_signals(facts, context)
    assert signals.single_ingredient_food is False


def test_single_ingredient_follows_context_when_set():
    facts = _facts()
    context = ProductContext(jurisdiction=Jurisdiction.india, single_ingredient=True)
    signals = retrieval_agent.derive_signals(facts, context)
    assert signals.single_ingredient_food is True


def test_imported_inferred_from_country_of_origin_fact_when_context_unset():
    facts = _facts(country_of_origin="Thailand")
    context = ProductContext(jurisdiction=Jurisdiction.india)
    signals = retrieval_agent.derive_signals(facts, context)
    assert signals.imported_product is True


def test_imported_false_when_no_signal_at_all():
    facts = _facts()
    context = ProductContext(jurisdiction=Jurisdiction.india)
    signals = retrieval_agent.derive_signals(facts, context)
    assert signals.imported_product is False


def test_allergen_keyword_detected_in_ingredients_text():
    facts = _facts(ingredients_text="Sugar, whole milk powder, cocoa mass")
    context = ProductContext(jurisdiction=Jurisdiction.uk)
    signals = retrieval_agent.derive_signals(facts, context)
    assert signals.contains_listed_allergen is True


def test_no_allergen_keyword_when_ingredients_are_clean():
    facts = _facts(ingredients_text="Water, sugar, citric acid")
    context = ProductContext(jurisdiction=Jurisdiction.uk)
    signals = retrieval_agent.derive_signals(facts, context)
    assert signals.contains_listed_allergen is False


def test_caffeine_trigger_detected():
    facts = _facts(ingredients_text="Water, sugar, caffeine, natural flavouring")
    context = ProductContext(jurisdiction=Jurisdiction.india)
    signals = retrieval_agent.derive_signals(facts, context)
    assert "caffeine" in signals.schedule_two_trigger
    assert "caffeine" in signals.warning_trigger


def test_date_marking_exempt_category_detected_from_product_name():
    facts = _facts(product_name="Aged Red Wine")
    context = ProductContext(jurisdiction=Jurisdiction.india)
    signals = retrieval_agent.derive_signals(facts, context)
    assert signals.date_marking_exempt_category is True


def test_always_applies_rule_is_applicable_regardless_of_signals():
    pack = rules.load_rule_pack(Jurisdiction.india)
    always_rule = next(r for r in pack.rules if r.applicability.always_applies)
    facts = _facts()
    context = ProductContext(jurisdiction=Jurisdiction.india)
    selected, _signals = retrieval_agent.select_rules(pack, facts, context)
    match = next(sr for sr in selected if sr.rule.rule_id == always_rule.rule_id)
    assert match.applicable is True


def test_conditional_rule_not_applicable_when_condition_fails():
    pack = rules.load_rule_pack(Jurisdiction.india)
    allergen_rule = next(r for r in pack.rules if r.rule_id == "RULE-IN-FOOD-011")
    facts = _facts(ingredients_text="Rice, water, salt")
    context = ProductContext(jurisdiction=Jurisdiction.india, imported=False, single_ingredient=False)
    selected, _signals = retrieval_agent.select_rules(pack, facts, context)
    match = next(sr for sr in selected if sr.rule.rule_id == allergen_rule.rule_id)
    assert match.applicable is False
    assert "Not applicable" in match.applicability_reason


def test_conditional_rule_applicable_when_condition_holds():
    pack = rules.load_rule_pack(Jurisdiction.india)
    facts = _facts(ingredients_text="Wheat flour, milk powder, sugar")
    context = ProductContext(jurisdiction=Jurisdiction.india, imported=False, single_ingredient=False)
    selected, _signals = retrieval_agent.select_rules(pack, facts, context)
    match = next(sr for sr in selected if sr.rule.rule_id == "RULE-IN-FOOD-011")
    assert match.applicable is True


def test_select_rules_returns_one_entry_per_pack_rule():
    pack = rules.load_rule_pack(Jurisdiction.uk)
    facts = _facts()
    context = ProductContext(jurisdiction=Jurisdiction.uk)
    selected, _signals = retrieval_agent.select_rules(pack, facts, context)
    assert len(selected) == len(pack.rules)
