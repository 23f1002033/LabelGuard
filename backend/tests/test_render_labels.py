import hashlib
import importlib.util
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "scripts" / "render_labels.py"

_spec = importlib.util.spec_from_file_location("render_labels", SPEC_PATH)
render_labels = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render_labels)


def test_render_is_deterministic(tmp_path):
    case = json.loads((ROOT / "evaluation" / "cases" / "IN-001.json").read_text())
    out1 = tmp_path / "a.png"
    out2 = tmp_path / "b.png"
    render_labels.render_case(case, out1, seed=1)
    render_labels.render_case(case, out2, seed=1)
    assert hashlib.sha256(out1.read_bytes()).hexdigest() == hashlib.sha256(out2.read_bytes()).hexdigest()


def test_rendered_image_has_positive_size(tmp_path):
    case = json.loads((ROOT / "evaluation" / "cases" / "IN-004.json").read_text())
    out = tmp_path / "c.png"
    render_labels.render_case(case, out, seed=2)
    img = Image.open(out)
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_missing_net_quantity_case_omits_that_text(tmp_path):
    case = json.loads((ROOT / "evaluation" / "cases" / "IN-002.json").read_text())
    all_text = json.dumps(case)
    assert "Net Wt" not in all_text
