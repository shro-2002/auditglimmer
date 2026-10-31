"""Generate the AuditGlimmer demo/eval fixture set (deterministic, synthetic, CC0).

Outputs fixtures/images/*.png, fixtures/ledger.csv and fixtures/manifest.json.
Every image is rendered here, so masks are exact ground truth (the object layer IS the mask).
The `muse` block per object is the labelled visible-evidence ground truth, plus deliberate
failure cases (malformed JSON, forbidden fields, simulated timeout). These are fixtures, not
model output, and are labelled as such everywhere they surface.

Run: uv run --project backend python scripts/make_fixtures.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.providers.mask_utils import raster_to_svg_path  # noqa: E402

OUT = ROOT / "fixtures"
W, H = 1280, 800
FACILITY = "WH-01"


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=size)


def evidence(otype, mfr, model, serial, *, serial_readable=True, idents=None, cond=None, unc=None, conf=0.9):
    identifiers = list(idents or [])
    if serial:
        identifiers.append({"kind": "serial", "value": serial, "readable": serial_readable})
    return {"kind": "ok", "evidence": {
        "observed_object_type": otype, "visible_manufacturer": mfr, "visible_model": model,
        "visible_serial_number": serial, "visible_identifiers": identifiers,
        "visible_condition_observations": cond or [], "uncertainties": unc or [], "model_confidence": conf}}


SERIAL_UNREADABLE = [{"field": "visible_serial_number", "note": "serial region illegible (blurred/scratched)"}]

SCENES = [
    {"file": "bay_a_generators.png", "title": "Bay A - standby generators", "seed": 11, "objects": [
        {"concept": "generator", "case": "exact_identifier_match", "true_asset_id": "A-001", "x": 70, "y": 300,
         "w": 270, "h": 230, "color": (196, 152, 38), "plate": ("CUMBERLAND", "PX-500", "S/N GN-48213"),
         "plate_mode": "clear", "confidence": 0.95,
         "muse": evidence("industrial generator", "Cumberland", "PX-500", "GN-48213",
                          cond=["surface rust on lower left panel"])},
        {"concept": "generator", "case": "unreadable_serial_unique_model", "true_asset_id": "A-002", "x": 380,
         "y": 320, "w": 250, "h": 210, "color": (58, 120, 170), "plate": ("BRIGHTWATER", "BW-300", "S/N GN-21094"),
         "plate_mode": "blur_serial", "confidence": 0.91,
         "muse": evidence("generator", "Brightwater", "BW-300", None, unc=SERIAL_UNREADABLE, conf=0.7)},
        {"concept": "generator", "case": "conflicting_ledger_serial", "true_asset_id": "A-003", "x": 670, "y": 290,
         "w": 280, "h": 240, "color": (196, 152, 38), "plate": ("CUMBERLAND", "PX-750", "S/N GN-55011"),
         "plate_mode": "clear", "confidence": 0.93,
         "muse": evidence("industrial generator", "Cumberland", "PX-750", "GN-55011")},
        {"concept": "generator", "case": "duplicate_observation_first_view", "true_asset_id": "A-007", "x": 990,
         "y": 330, "w": 230, "h": 200, "color": (58, 120, 170), "plate": ("BRIGHTWATER", "BW-400", "S/N GN-70707"),
         "plate_mode": "clear", "confidence": 0.9,
         "muse": evidence("generator", "Brightwater", "BW-400", "GN-70707")},
        {"concept": "generator", "case": "malformed_provider_response", "true_asset_id": "A-015", "x": 520,
         "y": 580, "w": 220, "h": 170, "color": (120, 128, 136), "plate": ("CUMBERLAND", "PX-300", "S/N GN-15015"),
         "plate_mode": "clear", "confidence": 0.88,
         "muse": {"kind": "malformed", "raw": '{"observed_object_type": "generator", "visible_manufacturer": "Cumber'}},
    ]},
    {"file": "bay_b_forklifts.png", "title": "Bay B - forklift line", "seed": 23, "objects": [
        {"concept": "forklift", "case": "serial_match_conflicting_manufacturer", "true_asset_id": "A-010",
         "x": 60, "y": 300, "w": 230, "h": 300, "color": (214, 120, 30), "plate": ("HOISTLINE", "LM-25", "S/N FL-7781"),
         "plate_mode": "clear", "confidence": 0.94, "kind": "forklift",
         "muse": evidence("forklift", "Hoistline", "LM-25", "FL-7781")},
        {"concept": "forklift", "case": "similar_looking_distinct_assets", "true_asset_id": "A-011", "x": 320,
         "y": 300, "w": 230, "h": 300, "color": (230, 190, 40), "plate": ("LIFTMASTER", "LM-25", "S/N FL-7790"),
         "plate_mode": "blur_serial", "confidence": 0.92, "kind": "forklift",
         "muse": evidence("forklift", "Liftmaster", "LM-25", None, unc=SERIAL_UNREADABLE, conf=0.75)},
        {"concept": "forklift", "case": "similar_looking_distinct_assets", "true_asset_id": "A-012", "x": 580,
         "y": 300, "w": 230, "h": 300, "color": (230, 190, 40), "plate": ("LIFTMASTER", "LM-25", "S/N FL-7791"),
         "plate_mode": "blur_serial", "confidence": 0.9, "kind": "forklift",
         "muse": evidence("forklift", "Liftmaster", "LM-25", None, unc=SERIAL_UNREADABLE, conf=0.74)},
        {"concept": "forklift", "case": "no_visible_identifiers", "true_asset_id": "A-013", "x": 840, "y": 320,
         "w": 200, "h": 270, "color": (90, 140, 80), "plate": None, "plate_mode": "none", "confidence": 0.86,
         "kind": "forklift",
         "muse": evidence("forklift", None, None, None, unc=[{"field": None, "note": "no nameplate visible"}],
                          conf=0.6)},
        {"concept": "forklift", "case": "provider_timeout", "true_asset_id": "A-014", "x": 1060, "y": 330,
         "w": 190, "h": 260, "color": (214, 120, 30), "plate": ("LIFTMASTER", "LM-30", "S/N FL-8890"),
         "plate_mode": "clear", "confidence": 0.89, "kind": "forklift", "muse": {"kind": "timeout"}},
    ]},
    {"file": "yard_c_mixed.png", "title": "Yard C - mixed equipment", "seed": 37, "objects": [
        {"concept": "generator", "case": "observed_not_in_register", "true_asset_id": None, "x": 60, "y": 330,
         "w": 250, "h": 210, "color": (150, 60, 60), "plate": ("VOLTANE", "VG-90", "S/N GN-90001"),
         "plate_mode": "clear", "confidence": 0.92,
         "muse": evidence("generator", "Voltane", "VG-90", "GN-90001")},
        {"concept": "generator", "case": "contradictory_ledger_duplicate_serial", "true_asset_id": "A-005",
         "x": 340, "y": 310, "w": 260, "h": 230, "color": (196, 152, 38), "plate": ("CUMBERLAND", "PX-500", "S/N GN-31337"),
         "plate_mode": "clear", "confidence": 0.93,
         "muse": evidence("industrial generator", "Cumberland", "PX-500", "GN-31337")},
        {"concept": "generator", "case": "exact_identifier_match", "true_asset_id": "A-004", "x": 630, "y": 320,
         "w": 250, "h": 220, "color": (58, 120, 170), "plate": ("BRIGHTWATER", "BW-220", "S/N GN-62040"),
         "plate_mode": "clear", "confidence": 0.94,
         "muse": evidence("generator", "Brightwater", "BW-220", "GN-62040", cond=["dent on top right corner"])},
        {"concept": "generator", "case": "duplicate_observation_second_view", "true_asset_id": "A-007", "x": 910,
         "y": 340, "w": 220, "h": 190, "color": (58, 120, 170), "plate": ("BRIGHTWATER", "BW-400", "S/N GN-70707"),
         "plate_mode": "clear", "confidence": 0.87,
         "muse": evidence("generator", "Brightwater", "BW-400", "GN-70707")},
        {"concept": "generator", "case": "unsupported_model_conclusion", "true_asset_id": "A-009", "x": 420,
         "y": 590, "w": 230, "h": 170, "color": (196, 152, 38), "plate": ("CUMBERLAND", "PX-500", "S/N GN-90909"),
         "plate_mode": "clear", "confidence": 0.9,
         "muse": {"kind": "unsupported", "raw": json.dumps({
             "observed_object_type": "generator", "visible_manufacturer": "Cumberland", "visible_model": "PX-500",
             "visible_serial_number": "GN-90909", "visible_identifiers": [], "visible_condition_observations": [],
             "uncertainties": [], "model_confidence": 0.9, "estimated_value_usd": 42000,
             "legal_owner": "Northwind Bank"})}},
        {"concept": "forklift", "case": "forklift_in_yard_unregistered", "true_asset_id": None, "x": 1140,
         "y": 600, "w": 120, "h": 170, "color": (90, 140, 80), "plate": None, "plate_mode": "none",
         "confidence": 0.71, "kind": "forklift",
         "muse": evidence("pallet jack", None, None, None,
                          unc=[{"field": None, "note": "partially out of frame; may not be a forklift"}], conf=0.4)},
    ]},
]

LEDGER = [
    # asset_id, type, mfr, model, serial, facility, location, value, currency, date
    ("A-001", "Industrial generator", "Cumberland", "PX-500", "GN-48213", FACILITY, "Bay A", "48000", "USD", "2026-10-01"),
    ("A-002", "Generator", "Brightwater", "BW-300", "GN-21094", FACILITY, "Bay A", "36500", "USD", "2026-10-01"),
    ("A-003", "Generator", "Cumberland", "PX-750", "GN-55017", FACILITY, "Bay A", "61000", "USD", "2026-10-01"),
    ("A-004", "Generator", "Brightwater", "BW-220", "GN-62040", FACILITY, "Yard C", "29900", "USD", "2026-10-01"),
    ("A-005", "Generator", "Cumberland", "PX-500", "GN-31337", FACILITY, "Yard C", "47000", "USD", "2026-10-01"),
    ("A-006", "Generator", "Cumberland", "PX-500", "GN-31337", FACILITY, "Bay D", "47000", "USD", "2026-10-01"),
    ("A-007", "Generator", "Brightwater", "BW-400", "GN-70707", FACILITY, "Bay A", "52000", "USD", "2026-10-01"),
    ("A-008", "Generator", "Voltane", "VG-60", "GN-80808", FACILITY, "Bay D", "33000", "USD", "2026-10-01"),
    ("A-009", "Generator", "Cumberland", "PX-500", "GN-90909", FACILITY, "Yard C", "47500", "USD", "2026-10-01"),
    ("A-010", "Forklift", "Liftmaster", "LM-25", "FL-7781", FACILITY, "Bay B", "21000", "USD", "2026-10-01"),
    ("A-011", "Forklift", "Liftmaster", "LM-25", "FL-7790", FACILITY, "Bay B", "21000", "USD", "2026-10-01"),
    ("A-012", "Forklift", "Liftmaster", "LM-25", "FL-7791", FACILITY, "Bay B", "21000", "USD", "2026-10-01"),
    ("A-013", "Forklift", "Hoistline", "HX-18", "FL-6612", FACILITY, "Bay B", "18500", "USD", "2026-10-01"),
    ("A-014", "Forklift", "Liftmaster", "LM-30", "FL-8890", FACILITY, "Bay B", "24000", "USD", "2026-10-01"),
    ("A-015", "Generator", "Cumberland", "PX-300", "GN-15015", FACILITY, "Bay A", "31000", "USD", "2026-10-01"),
    ("A-020", "Pallet racking", "Rackwell", "RW-12", "", FACILITY, "Bay D", "9000", "USD", "2026-10-01"),
    ("A-021", "Generator", "Cumberland", "PX-500", "GN-40404", "WH-02", "Dock 2", "47000", "USD", "2026-10-01"),
    # deliberately problematic rows (validation test cases)
    ("", "Generator", "Cumberland", "PX-500", "GN-00000", FACILITY, "Bay A", "1000", "USD", "2026-10-01"),
    ("A-022", "Air compressor", "Atlasco", "AC-7", "AC-77001", FACILITY,
     '=HYPERLINK("http://example.invalid","click")', "-500", "usd", "31/10/2026"),
    ("A-001", "Generator", "Cumberland", "PX-500", "GN-48213", FACILITY, "Bay A", "48000", "USD", "2026-10-01"),
]


def draw_background(img: Image.Image, rng: random.Random) -> None:
    d = ImageDraw.Draw(img)
    for y in range(H):  # wall-to-floor gradient
        t = y / H
        base = (int(46 + 30 * t), int(50 + 28 * t), int(56 + 22 * t)) if y < 260 else (int(92 - 20 * t), int(90 - 20 * t), int(84 - 18 * t))
        d.line([(0, y), (W, y)], fill=base)
    for x in range(0, W, 160):  # racking uprights on the back wall
        d.rectangle([x + 10, 40, x + 22, 255], fill=(70, 90, 120))
        for yy in range(70, 250, 60):
            d.rectangle([x + 10, yy, x + 170, yy + 8], fill=(160, 90, 40))
    for x in range(0, W, 240):
        d.line([(x, 260), (x - 200, H)], fill=(110, 108, 100), width=2)
    d.rectangle([0, 262, W, 270], fill=(200, 180, 40))  # safety line
    noise = Image.effect_noise((W, H), 18).convert("RGB")
    img.paste(Image.blend(img, noise, 0.06))


def draw_generator(d: ImageDraw.ImageDraw, m: ImageDraw.ImageDraw, o: dict) -> tuple[int, int, int, int]:
    x, y, w, h = o["x"], o["y"], o["w"], o["h"]
    body = [x, y + 20, x + w, y + h]
    for draw, fill in ((d, o["color"]), (m, 1)):
        draw.rounded_rectangle(body, radius=14, fill=fill)
        draw.rectangle([x + w - 50, y, x + w - 32, y + 24], fill=(60, 60, 60) if draw is d else 1)  # exhaust
        draw.rectangle([x + 10, y + h, x + 30, y + h + 10], fill=(30, 30, 30) if draw is d else 1)  # feet
        draw.rectangle([x + w - 30, y + h, x + w - 10, y + h + 10], fill=(30, 30, 30) if draw is d else 1)
    shade = tuple(max(0, c - 50) for c in o["color"])
    for i in range(6):
        gx = x + 20 + i * 14
        d.rectangle([gx, y + 50, gx + 7, y + h - 30], fill=shade)
    return x + w // 2 - 20, y + 60, x + w - 16, y + 60 + 74


def draw_forklift(d: ImageDraw.ImageDraw, m: ImageDraw.ImageDraw, o: dict) -> tuple[int, int, int, int]:
    x, y, w, h = o["x"], o["y"], o["w"], o["h"]
    for draw, is_mask in ((d, False), (m, True)):
        c = (lambda col: 1) if is_mask else (lambda col: col)
        draw.rectangle([x + 10, y, x + 26, y + h - 40], fill=c((80, 80, 85)))  # mast
        draw.rectangle([x + 34, y, x + 50, y + h - 40], fill=c((80, 80, 85)))
        draw.rectangle([x, y + h - 70, x + 70, y + h - 60], fill=c((60, 60, 60)))  # fork
        draw.rectangle([x + 54, y + h // 3, x + w, y + h - 40], fill=c(o["color"]))  # body
        draw.rectangle([x + 80, y + h // 3 - 90, x + w - 20, y + h // 3 - 80], fill=c((40, 40, 40)))  # guard
        draw.rectangle([x + 84, y + h // 3 - 90, x + 92, y + h // 3], fill=c((40, 40, 40)))
        draw.rectangle([x + w - 30, y + h // 3 - 90, x + w - 22, y + h // 3], fill=c((40, 40, 40)))
        for cx in (x + 90, x + w - 40):
            draw.ellipse([cx - 28, y + h - 64, cx + 28, y + h - 8], fill=c((25, 25, 25)))
    return x + 110, y + h // 3 + 20, x + w - 12, y + h // 3 + 20 + 66


def draw_plate(img: Image.Image, box: tuple[int, int, int, int], lines: tuple[str, str, str], mode: str) -> None:
    d = ImageDraw.Draw(img)
    d.rectangle(box, fill=(232, 232, 224), outline=(30, 30, 30), width=2)
    sizes = (15, 15, 14)
    ty = box[1] + 4
    for text, size in zip(lines, sizes):
        d.text((box[0] + 6, ty), text, fill=(20, 20, 20), font=font(size))
        ty += size + 6
    if mode == "blur_serial":
        region = (box[0] + 2, box[1] + 44, box[2] - 2, box[3] - 2)
        patch = img.crop(region).filter(ImageFilter.GaussianBlur(5))
        img.paste(patch, region[:2])


def render_scene(scene: dict) -> dict:
    rng = random.Random(scene["seed"])
    img = Image.new("RGB", (W, H))
    draw_background(img, rng)
    d = ImageDraw.Draw(img)
    d.text((24, 12), scene["title"] + "  [synthetic AuditGlimmer fixture]", fill=(220, 225, 230), font=font(18))
    objects = []
    for index, o in enumerate(scene["objects"], start=1):
        mask = Image.new("1", (W, H), 0)
        md = ImageDraw.Draw(mask)
        plate_box = (draw_forklift if o.get("kind") == "forklift" else draw_generator)(d, md, o)
        if o["plate"]:
            draw_plate(img, plate_box, o["plate"], o["plate_mode"])
        bbox = mask.getbbox()
        raster = mask.crop(bbox)
        rw, rh = raster.size
        bits = [1 if v else 0 for v in raster.convert("L").tobytes()]
        objects.append({
            "object_index": index, "concept": o["concept"], "case": o["case"], "true_asset_id": o["true_asset_id"],
            "bounds": list(bbox), "raster_w": rw, "raster_h": rh, "area_px": sum(bits),
            "svg_path": raster_to_svg_path(bits, rw, rh), "confidence": o["confidence"], "muse": o["muse"],
            "plate_text": list(o["plate"]) if o["plate"] else None, "plate_mode": o["plate_mode"],
        })
        d = ImageDraw.Draw(img)
    path = OUT / "images" / scene["file"]
    img.save(path, format="PNG", optimize=True)
    data = path.read_bytes()
    return {"file": scene["file"], "title": scene["title"], "sha256": hashlib.sha256(data).hexdigest(),
            "width": W, "height": H, "facility_id": FACILITY, "objects": objects}


def write_ledger() -> None:
    header = ["asset_id", "asset_type", "manufacturer", "model", "serial_number", "facility_id",
              "expected_location", "ledger_value", "currency", "inspection_date"]
    with (OUT / "ledger.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(LEDGER)


EXPECTED_ASSET_STATUS = {  # correct handling after inspecting BOTH concepts, before any human review
    "A-001": "VERIFIED", "A-002": "PROBABLE", "A-003": "MISMATCHED", "A-004": "VERIFIED", "A-005": "PROBABLE",
    "A-006": "PROBABLE", "A-007": "PROBABLE", "A-008": "UNVERIFIED", "A-009": "UNVERIFIED", "A-010": "MISMATCHED",
    "A-011": "PROBABLE", "A-012": "PROBABLE", "A-013": "UNVERIFIED", "A-014": "UNVERIFIED", "A-015": "UNVERIFIED",
    "A-020": "NOT_OBSERVABLE", "A-021": "NOT_OBSERVABLE", "A-022": "NOT_OBSERVABLE",
}


def main() -> None:
    (OUT / "images").mkdir(parents=True, exist_ok=True)
    images = [render_scene(s) for s in SCENES]
    write_ledger()
    manifest = {
        "version": 1,
        "license": "CC0-1.0. Synthetic images rendered by scripts/make_fixtures.py; no third-party content.",
        "note": "Fixture labels are authored ground truth, not model output. 'muse' blocks include deliberate "
                "failure cases for testing.",
        "facility_id": FACILITY, "concepts": ["generator", "forklift"], "images": images,
        "expected_asset_status": EXPECTED_ASSET_STATUS,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"wrote {len(images)} images, {len(LEDGER)} ledger rows, manifest to {OUT}")


if __name__ == "__main__":
    main()
