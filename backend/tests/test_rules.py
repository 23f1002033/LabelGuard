from app.models.schemas import FACT_NAMES, Jurisdiction
from app.services import rules


def test_india_pack_loads():
    pack = rules.load_rule_pack(Jurisdiction.india)
    assert pack.jurisdiction == Jurisdiction.india
    assert len(pack.rules) >= 10
    assert len(pack.sources) >= 1


def test_uk_pack_loads():
    pack = rules.load_rule_pack(Jurisdiction.uk)
    assert pack.jurisdiction == Jurisdiction.uk
    assert len(pack.rules) >= 10


def test_rule_ids_are_unique_per_pack():
    for jurisdiction in (Jurisdiction.india, Jurisdiction.uk):
        pack = rules.load_rule_pack(jurisdiction)
        ids = [r.rule_id for r in pack.rules]
        assert len(ids) == len(set(ids))


def test_every_rule_source_id_exists_in_sources():
    for jurisdiction in (Jurisdiction.india, Jurisdiction.uk):
        pack = rules.load_rule_pack(jurisdiction)
        source_ids = {s.source_id for s in pack.sources}
        for rule in pack.rules:
            assert rule.source_id in source_ids


def test_every_required_fact_is_known():
    known = set(FACT_NAMES)
    for jurisdiction in (Jurisdiction.india, Jurisdiction.uk):
        pack = rules.load_rule_pack(jurisdiction)
        for rule in pack.rules:
            for fact in rule.required_facts:
                assert fact in known, f"{rule.rule_id} references unknown fact {fact}"


def test_conditional_rules_declare_conditions():
    for jurisdiction in (Jurisdiction.india, Jurisdiction.uk):
        pack = rules.load_rule_pack(jurisdiction)
        for rule in pack.rules:
            if not rule.applicability.always_applies:
                assert len(rule.applicability.conditions) >= 1, rule.rule_id


def test_source_lookup_returns_name_and_url():
    pack = rules.load_rule_pack(Jurisdiction.india)
    lookup = rules.source_lookup(pack)
    for rule in pack.rules:
        name, url = lookup[rule.source_id]
        assert name
        assert url.startswith("http")
