from __future__ import annotations

import json
from functools import lru_cache

from app.config import settings
from app.models.schemas import Jurisdiction, RulePack

_PACK_FILES = {
    Jurisdiction.india: "india/food_label_rules.json",
    Jurisdiction.uk: "uk/food_label_rules.json",
}


@lru_cache(maxsize=None)
def load_rule_pack(jurisdiction: Jurisdiction) -> RulePack:
    path = settings.rules_dir / _PACK_FILES[jurisdiction]
    data = json.loads(path.read_text())
    return RulePack.model_validate(data)


def source_lookup(pack: RulePack) -> dict[str, tuple[str, str]]:
    return {s.source_id: (s.name, s.url) for s in pack.sources}
