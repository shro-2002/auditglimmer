"""One approved Muse Spark call on the CC BY-SA nameplate close-up (identifier extraction test).

Run: uv run --project backend python eval/live_muse_nameplate.py --i-approve-spend
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import load_dotenv  # noqa: E402
from app.errors import ProviderError  # noqa: E402
from app.pipeline import make_crop  # noqa: E402
from app.providers.base import CropContext, ImageInput  # noqa: E402
from app.providers.meta_http import MetaHttp  # noqa: E402
from app.providers.muse_meta import MetaMuseProvider  # noqa: E402

LABEL = {"visible_serial_number": "5735", "visible_manufacturer": None, "visible_model": None,
         "other_visible_fields": {"AMP": "16", "VOLT": "70", "GIRI": "1000"}}

if "--i-approve-spend" not in sys.argv:
    raise SystemExit("REFUSED: pass --i-approve-spend")
load_dotenv()
path = ROOT / "fixtures" / "real" / "generator_nameplate_ccbysa.jpg"
data = path.read_bytes()
from PIL import Image  # noqa: E402

w, h = Image.open(path).size
image = ImageInput(data, "image/jpeg", w, h, hashlib.sha256(data).hexdigest())
crop, box = make_crop(image, (0, 0, w, h))  # whole plate, same crop path as the app
out: dict = {"image": path.name, "label": LABEL, "label_source": "assistant visual reading (not independent human)"}
try:
    res = MetaMuseProvider(MetaHttp(os.environ["MODEL_API_KEY"], 90, 0)).extract_visual_evidence(
        crop, CropContext(image.sha256, 0, box, "generator nameplate"))
    out.update(evidence=res.evidence.model_dump(), latency_ms=round(res.meta.latency_ms),
               tokens=[res.meta.input_tokens, res.meta.output_tokens], est_cost=res.meta.estimated_cost_usd,
               request_id_present=bool(res.meta.request_id), finish_reason=res.meta.extra.get("finish_reason"))
except ProviderError as exc:
    out["error"] = f"{exc.kind}: {exc.message}"
(ROOT / "eval" / "results" / "live-muse-nameplate.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=1)[:2500])
