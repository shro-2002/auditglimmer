"""Gate 9 live smoke test against Meta Model API. PAID: refuses to run without explicit approval.

Makes at most 1 SAM 3.1 call (one fixture image) + up to --max-extractions Muse Spark calls.
Worst-case estimate (default 3 extractions): 1 x $0.0025 + 3 x ~$0.0123 (3k in / 2k out tokens) ~= $0.04.

Requires all of:
  MODEL_API_KEY            (never printed)
  AUDITGLIMMER_LIVE_APPROVED=1
  --i-approve-spend        on the command line

Run: uv run --project backend python scripts/live_smoke.py --i-approve-spend
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import SAM_USD_PER_IMAGE, load_dotenv  # noqa: E402
from app.errors import ProviderError  # noqa: E402
from app.pipeline import EST_EXTRACT_USD, make_crop  # noqa: E402
from app.providers.base import CropContext, ImageInput  # noqa: E402
from app.providers.meta_http import MetaHttp  # noqa: E402
from app.providers.muse_meta import MetaMuseProvider  # noqa: E402
from app.providers.sam_meta import MetaSAMProvider  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--i-approve-spend", action="store_true")
    ap.add_argument("--image", default="bay_a_generators.png")
    ap.add_argument("--concept", default="generator")
    ap.add_argument("--max-extractions", type=int, default=3)
    args = ap.parse_args()
    load_dotenv()  # auditglimmer/.env; real environment variables take precedence
    key = os.environ.get("MODEL_API_KEY", "")
    worst = SAM_USD_PER_IMAGE + args.max_extractions * EST_EXTRACT_USD
    print(f"credentials present: {bool(key)}; worst-case estimated spend: ${worst:.4f}")
    if not (key and os.environ.get("AUDITGLIMMER_LIVE_APPROVED") == "1" and args.i_approve_spend):
        print("REFUSED: need MODEL_API_KEY, AUDITGLIMMER_LIVE_APPROVED=1 and --i-approve-spend. No request sent.")
        return 2
    http = MetaHttp(key, timeout_s=90, max_retries=1)
    data = (ROOT / "fixtures" / "images" / args.image).read_bytes()
    from PIL import Image
    import io

    with Image.open(io.BytesIO(data)) as im:
        w, h = im.size
    image = ImageInput(data, "image/png", w, h, hashlib.sha256(data).hexdigest())
    out: dict = {"image": args.image, "concept": args.concept}
    try:
        seg = MetaSAMProvider(http).segment_image(image, args.concept)
    except ProviderError as exc:
        out["sam_error"] = f"{exc.kind}: {exc.message}"
        print(json.dumps(out, indent=2))
        return 1
    out["sam"] = {"objects": len(seg.objects), "latency_ms": round(seg.meta.latency_ms), "usage": seg.meta.extra,
                  "boxes": [o.mask.bounds for o in seg.objects], "confidence": [o.confidence for o in seg.objects]}
    muse = MetaMuseProvider(http)
    out["extractions"] = []
    for obj in seg.objects[: args.max_extractions]:
        crop, box = make_crop(image, obj.mask.bounds)
        try:
            res = muse.extract_visual_evidence(crop, CropContext(image.sha256, obj.object_index, box, args.concept))
            out["extractions"].append({"object": obj.object_index, "evidence": res.evidence.model_dump(),
                                       "tokens": [res.meta.input_tokens, res.meta.output_tokens],
                                       "est_cost": res.meta.estimated_cost_usd, "latency_ms": round(res.meta.latency_ms)})
        except ProviderError as exc:
            out["extractions"].append({"object": obj.object_index, "error": f"{exc.kind}: {exc.message}"})
    dest = ROOT / "eval" / "results" / "live-smoke.json"
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
