from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "evaluation" / "cases"
IMAGES_DIR = ROOT / "evaluation" / "images"

MARGIN_PX = 24
PANEL_GAP_PX = 20
LINE_GAP_PX = 6

SYMBOL_COLORS = {
    "veg_green": "#0a7d1f",
    "nonveg_brown": "#7a3b1e",
}


def _font(size_px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=max(8, int(size_px)))


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _draw_symbol(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, symbol: str) -> int:
    if symbol == "veg_green":
        color = SYMBOL_COLORS["veg_green"]
        draw.rectangle([x, y, x + size, y + size], outline=color, width=max(2, size // 12))
        cx, cy, r = x + size / 2, y + size / 2, size * 0.32
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    elif symbol == "nonveg_brown":
        color = SYMBOL_COLORS["nonveg_brown"]
        draw.rectangle([x, y, x + size, y + size], outline=color, width=max(2, size // 12))
        cx, top, half = x + size / 2, y + size * 0.2, size * 0.32
        draw.polygon(
            [(cx, top), (cx - half, top + half * 1.6), (cx + half, top + half * 1.6)],
            fill=color,
        )
    elif symbol == "fssai_logo":
        color = "#1b5fa8"
        draw.ellipse([x, y, x + size, y + size], outline=color, width=max(2, size // 10))
        font = _font(int(size * 0.32))
        draw.text((x + size * 0.14, y + size * 0.3), "FSSAI", font=font, fill=color)
    return size


def render_case(case: dict, image_path: Path, seed: int) -> None:
    spec = case["label_spec"]
    pack = spec["pack"]
    px_per_cm = pack["px_per_cm"]
    width_px = max(320, int(pack["width_cm"] * px_per_cm))

    blocks_layout: list[tuple[str, dict]] = []
    for panel in spec["panels"]:
        blocks_layout.append(("panel_start", {"id": panel["id"]}))
        for block in panel["blocks"]:
            blocks_layout.append((block["type"], block))
        blocks_layout.append(("panel_end", {}))

    measure_img = Image.new("RGB", (width_px, 10), "white")
    measure_draw = ImageDraw.Draw(measure_img)

    height_px = MARGIN_PX
    for kind, block in blocks_layout:
        if kind == "panel_start":
            height_px += PANEL_GAP_PX
        elif kind == "panel_end":
            height_px += PANEL_GAP_PX
        elif kind == "text":
            font = _font(block.get("font_px", 16))
            text = block["text"].upper() if block.get("uppercase") else block["text"]
            lines = _wrap_text(measure_draw, text, font, width_px - 2 * MARGIN_PX)
            line_height = measure_draw.textbbox((0, 0), "Ag", font=font)[3] + LINE_GAP_PX
            height_px += line_height * len(lines)
        elif kind == "symbol":
            height_px += block.get("height_px", 30) + LINE_GAP_PX
        elif kind == "spacer":
            height_px += block.get("height_px", 10)
    height_px += MARGIN_PX

    background = pack.get("background", "#ffffff")
    img = Image.new("RGB", (width_px, height_px), background)
    draw = ImageDraw.Draw(img)

    y = MARGIN_PX
    for kind, block in blocks_layout:
        if kind == "panel_start":
            y += PANEL_GAP_PX
            draw.line([(MARGIN_PX, y), (width_px - MARGIN_PX, y)], fill="#cccccc", width=1)
        elif kind == "panel_end":
            y += PANEL_GAP_PX
        elif kind == "text":
            font = _font(block.get("font_px", 16))
            text = block["text"].upper() if block.get("uppercase") else block["text"]
            color = block.get("color", "#000000")
            lines = _wrap_text(draw, text, font, width_px - 2 * MARGIN_PX)
            line_height = draw.textbbox((0, 0), "Ag", font=font)[3] + LINE_GAP_PX
            for line in lines:
                draw.text((MARGIN_PX, y), line, font=font, fill=color)
                if block.get("bold"):
                    draw.text((MARGIN_PX + 1, y), line, font=font, fill=color)
                y += line_height
        elif kind == "symbol":
            size = block.get("height_px", 30)
            _draw_symbol(draw, MARGIN_PX, y, size, block["symbol"])
            y += size + LINE_GAP_PX
        elif kind == "spacer":
            y += block.get("height_px", 10)

    rotation = pack.get("rotation_degrees", 0)
    if rotation:
        img = img.rotate(rotation, expand=True, fillcolor=background)

    blur_radius = pack.get("blur_radius", 0)
    if blur_radius:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    noise = pack.get("noise", 0)
    if noise:
        rng = random.Random(seed)
        pixels = img.load()
        w, h = img.size
        for _ in range(int(w * h * noise)):
            px = rng.randrange(w)
            py = rng.randrange(h)
            shade = rng.randrange(0, 255)
            pixels[px, py] = (shade, shade, shade)

    image_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(image_path, format="PNG")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="render only this case_id")
    args = parser.parse_args()

    case_files = sorted(CASES_DIR.glob("*.json"))
    if args.case:
        case_files = [p for p in case_files if p.stem == args.case]
        if not case_files:
            print(f"no case file for {args.case}")
            return 1

    for path in case_files:
        case = json.loads(path.read_text())
        image_path = ROOT / case["image"]
        seed = int(hashlib.sha256(case["case_id"].encode()).hexdigest(), 16) % (2**31)
        render_case(case, image_path, seed)
        print(f"rendered {case['case_id']} -> {image_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
