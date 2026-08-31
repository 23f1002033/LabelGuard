import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(Path(path).read_text())


def check(instance_path, schema_path, errors):
    validator = Draft7Validator(load(schema_path))
    for error in sorted(validator.iter_errors(load(instance_path)), key=lambda e: e.path):
        errors.append(f"{instance_path}: {list(error.path)} {error.message}")


def main():
    errors = []
    rule_schema = ROOT / "rules" / "rule_pack.schema.json"
    packs = sorted(ROOT.glob("rules/*/food_label_rules.json"))
    if not packs:
        errors.append("no rule packs found")
    for pack in packs:
        check(pack, rule_schema, errors)

    for case in sorted((ROOT / "evaluation" / "cases").glob("*.json")):
        check(case, ROOT / "evaluation" / "case.schema.json", errors)
    for annotation in sorted((ROOT / "evaluation" / "annotations").glob("*.json")):
        check(annotation, ROOT / "evaluation" / "annotation.schema.json", errors)

    known_rule_ids = set()
    for pack in packs:
        known_rule_ids.update(rule["rule_id"] for rule in load(pack)["rules"])
    for annotation in sorted((ROOT / "evaluation" / "annotations").glob("*.json")):
        for expected in load(annotation)["expected_findings"]:
            if expected["rule_id"] not in known_rule_ids:
                errors.append(f"{annotation}: unknown rule_id {expected['rule_id']}")

    case_ids = {load(p)["case_id"] for p in (ROOT / "evaluation" / "cases").glob("*.json")}
    annotated = {load(p)["case_id"] for p in (ROOT / "evaluation" / "annotations").glob("*.json")}
    for missing in sorted(case_ids - annotated):
        errors.append(f"case {missing} has no annotation file")
    for orphan in sorted(annotated - case_ids):
        errors.append(f"annotation {orphan} has no case file")

    for path in list(ROOT.glob("rules/**/*.json")) + list(ROOT.glob("evaluation/**/*.json")):
        text = path.read_text()
        offenders = {c for c in text if ord(c) > 127}
        if offenders:
            errors.append(f"{path}: non-ascii characters {sorted(offenders)}")

    if errors:
        print("FAILED")
        for e in errors:
            print(" -", e)
        return 1
    print(f"OK: {len(packs)} rule packs, {len(case_ids)} cases, {len(annotated)} annotations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
