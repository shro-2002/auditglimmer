"""Inspection run: segment -> crop -> extract -> (reconcile on read). Runs in a worker thread.

Every provider request is persisted as a ProviderCallRow (timing, tokens, estimated cost, raw output
reference). LIVE runs are capped by request count and estimated USD before each call.
"""

from __future__ import annotations

import io
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps
from sqlalchemy import select

from .config import MUSE_USD_PER_INPUT_TOKEN, MUSE_USD_PER_OUTPUT_TOKEN, SAM_USD_PER_IMAGE, Settings
from .db import Database, DetectionRow, EvidenceRow, ImageRow, ProviderCallRow, RunEventRow, RunRow, new_id, utcnow
from .errors import ProviderError
from .providers.base import CallMeta, CropContext, ImageInput
from .reconcile import MIN_SERIAL_LEN, norm_id
from .schemas import EvidenceReference, ModelEvidence, VisualEvidence

log = logging.getLogger("auditglimmer.pipeline")
CROP_PAD_FRACTION = 0.08
CROP_MAX_SIDE = 1024
# Conservative per-extraction estimate used for pre-call budget checks (actual usage is recorded after).
EST_EXTRACT_USD = 3000 * MUSE_USD_PER_INPUT_TOKEN + 2000 * MUSE_USD_PER_OUTPUT_TOKEN
_RUN_SLOTS = threading.BoundedSemaphore(2)
_EXTRACT_LOCK = threading.Lock()


class BudgetExceeded(Exception):
    pass


@dataclass
class Budget:
    live: bool
    max_requests: int
    max_usd: float
    requests: int = 0
    usd: float = 0.0

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def reserve(self, est_usd: float) -> None:
        if not self.live:
            return
        with self._lock:
            if self.requests + 1 > self.max_requests or self.usd + est_usd > self.max_usd:
                raise BudgetExceeded(f"run budget reached ({self.requests} requests, ${self.usd:.4f} estimated)")
            self.requests += 1
            self.usd += est_usd

    def settle(self, est_usd: float, actual_usd: float | None) -> None:
        """Replace a reservation with the recorded actual cost when the provider reported usage."""
        if not self.live or actual_usd is None:
            return
        with self._lock:
            self.usd += max(actual_usd, 0.0) - est_usd


def make_crop(image: ImageInput, bounds: tuple[int, int, int, int]) -> tuple[ImageInput, tuple[int, int, int, int]]:
    x1, y1, x2, y2 = (max(0, min(v, lim)) for v, lim in zip(bounds, (image.width, image.height) * 2))
    if x2 <= x1 or y2 <= y1:
        raise ProviderError("invalid_output", f"degenerate or out-of-image mask bounds {tuple(bounds)}")
    pad_x, pad_y = int((x2 - x1) * CROP_PAD_FRACTION), int((y2 - y1) * CROP_PAD_FRACTION)
    box = (max(0, x1 - pad_x), max(0, y1 - pad_y), min(image.width, x2 + pad_x), min(image.height, y2 + pad_y))
    with Image.open(io.BytesIO(image.data)) as img:
        crop = img.convert("RGB").crop(box)
        crop.thumbnail((CROP_MAX_SIDE, CROP_MAX_SIDE))
        buf = io.BytesIO()
        crop.save(buf, format="JPEG", quality=90)
        data, (w, h) = buf.getvalue(), crop.size
    return ImageInput(data=data, media_type="image/jpeg", width=w, height=h, sha256=""), box


CONFIRM_VIEW = "re-cut from source photo, <=1536 px (small regions upscaled <=x2), autocontrast, unsharp mask"
CONFIRM_MAX_SIDE = 1536  # bounds image tokens: the second read must stay cheap


def make_confirm_view(source: ImageInput, box: tuple[int, int, int, int]) -> ImageInput:
    """Enhanced view for the second read, cut again from the SOURCE photo (not the 1024 px first-read crop):
    up to 1536 px, small regions upscaled up to x2, contrast-stretched and sharpened."""
    with Image.open(io.BytesIO(source.data)) as img:
        view = img.convert("RGB").crop(box)
        scale = min(2.0, CONFIRM_MAX_SIDE / max(view.size))
        view = view.resize((max(1, int(view.width * scale)), max(1, int(view.height * scale))), Image.LANCZOS)
        view = ImageOps.autocontrast(view, cutoff=1).filter(ImageFilter.UnsharpMask(radius=2, percent=120))
        buf = io.BytesIO()
        view.save(buf, format="JPEG", quality=92)
    return ImageInput(data=buf.getvalue(), media_type="image/jpeg", width=view.width, height=view.height, sha256="")


def needs_confirmation(evidence) -> bool:  # noqa: ANN001 - ModelEvidence
    """Only a single, certain, readable serial can reach Tier 1, so only those reads pay for a second call."""
    serial = norm_id(evidence.visible_serial_number)
    if not serial or len(serial) < MIN_SERIAL_LEN:
        return False
    if any(u.field == "visible_serial_number" for u in evidence.uncertainties):
        return False
    for ident in evidence.visible_identifiers:
        key = norm_id(ident.value)
        if ident.kind == "serial" and (not ident.readable and key == serial
                                       or ident.readable and key and len(key) >= MIN_SERIAL_LEN and key != serial):
            return False
    return True


def _second_read_missing(row: EvidenceRow) -> bool:
    """An ok first read whose required second read is absent or failed may be re-extracted (both reads)."""
    evidence = ModelEvidence.model_validate({k: v for k, v in row.evidence.items() if k != "evidence_references"})
    return needs_confirmation(evidence) and (row.confirmation or {}).get("status") != "ok"


class Pipeline:
    def __init__(self, settings: Settings, database: Database, seg, ext) -> None:  # noqa: ANN001
        self.settings, self.db, self.seg, self.ext = settings, database, seg, ext
        self.raw_dir = settings.data_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self._seq: dict[str, int] = {}
        # ponytail: in-memory run flag (no schema column); queued runs are reset to failed on restart anyway
        self.full_frame_runs: set[str] = set()
        self._seq_lock = threading.Lock()

    # ----- persistence helpers -----
    def event(self, run_id: str, stage: str, status: str, message: str, **kw) -> None:  # noqa: ANN003
        with self._seq_lock:
            seq = self._seq.get(run_id, 0) + 1
            self._seq[run_id] = seq
        with self.db.session() as s:
            s.add(RunEventRow(run_id=run_id, seq=seq, stage=stage, status=status, message=message[:1000], **kw))

    def record_call(self, *, session_id: str, run_id: str, operation: str, meta: CallMeta | None, status: str,
                    error: str | None, correlation_id: str, provider, raw: str | None = None,  # noqa: ANN001
                    latency_ms: float = 0.0, started_at: str) -> str:
        call_id = new_id("call")
        raw_text = raw if raw is not None else (meta.raw_output if meta else None)
        ref = None
        if raw_text is not None and (raw_text or self.settings.mode == "live"):  # keep empty live bodies auditable
            path = self.raw_dir / f"{call_id}.txt"
            path.write_text(raw_text)
            ref = str(path.relative_to(self.settings.data_dir))
        with self.db.session() as s:
            s.add(ProviderCallRow(
                id=call_id, session_id=session_id, run_id=run_id, provider=provider.name, model=provider.model,
                mode=self.settings.mode, operation=operation, status=status,
                latency_ms=meta.latency_ms if meta and meta.latency_ms else latency_ms, started_at=started_at,
                input_tokens=meta.input_tokens if meta else None, output_tokens=meta.output_tokens if meta else None,
                images=meta.images if meta else 1, estimated_cost_usd=meta.estimated_cost_usd if meta else 0.0,
                error=error, raw_output_ref=ref, correlation_id=correlation_id))
        return call_id

    # ----- spend control -----
    def budget_for(self, session_id: str, max_requests: int, max_usd: float) -> Budget:
        """Budget bounded by the per-call caps AND persistent per-session / all-time live totals."""
        live = self.settings.mode == "live"
        if not live:
            return Budget(False, max_requests, max_usd)
        with self.db.session() as s:
            calls = s.scalars(select(ProviderCallRow).where(ProviderCallRow.mode == "live")).all()
        session_requests = sum(1 for c in calls if c.session_id == session_id)
        total_usd = sum(c.estimated_cost_usd for c in calls)
        remaining_requests = max(0, self.settings.max_live_requests_per_session - session_requests)
        remaining_usd = max(0.0, self.settings.max_live_usd_total - total_usd)
        return Budget(True, min(max_requests, remaining_requests), min(max_usd, remaining_usd))

    def extract_one(self, detection_id: str) -> bool:
        """Synchronous evidence extraction for one detection (user-selected region).

        Serialized process-wide so concurrent clicks cannot double-spend or race the unique evidence row.
        """
        with _EXTRACT_LOCK:
            return self._extract_one(detection_id)

    def _extract_one(self, detection_id: str) -> bool:
        with self.db.session() as s:
            det = s.get(DetectionRow, detection_id)
            if det is None:
                raise LookupError(detection_id)
            run = s.get(RunRow, det.run_id)
            img = s.get(ImageRow, det.image_id)
            if det.evidence is not None and det.evidence.status == "ok" and not _second_read_missing(det.evidence):
                raise FileExistsError(detection_id)
            if det.evidence is not None:  # replace a failed attempt (or a missing/failed second read) with the retry
                s.delete(det.evidence)
            session_id, corr, concept = run.session_id, run.correlation_id, run.concept
            image_input = ImageInput(Path(img.stored_path).read_bytes(), img.media_type, img.width, img.height,
                                     img.sha256)
        budget = self.budget_for(session_id, 2, 2 * EST_EXTRACT_USD)  # first read + second read
        with self.db.session() as s:
            det = s.get(DetectionRow, detection_id)
            return self._extract(run.id, session_id, corr, image_input, det, concept, budget)

    # ----- run -----
    def start(self, run_id: str) -> threading.Thread:
        thread = threading.Thread(target=self._run_guarded, args=(run_id,), daemon=True, name=f"run-{run_id}")
        thread.start()
        return thread

    def _run_guarded(self, run_id: str) -> None:
        with _RUN_SLOTS:
            try:
                self._run(run_id)
            except Exception as exc:  # last-resort: never leave a run "running"
                log.exception("run %s crashed", run_id)
                try:
                    self.event(run_id, "run", "error", f"internal error: {type(exc).__name__}")
                    self._finish(run_id, "failed", f"internal error: {type(exc).__name__}")
                except Exception:  # session deleted mid-run: nothing left to update
                    log.warning("run %s could not record failure (session deleted?)", run_id)

    def _finish(self, run_id: str, status: str, error: str | None) -> None:
        with self.db.session() as s:
            run = s.get(RunRow, run_id)
            if run is not None:
                run.status, run.finished_at, run.error = status, utcnow(), error

    def _run(self, run_id: str) -> None:
        with self.db.session() as s:
            run = s.get(RunRow, run_id)
            if run is None:
                return  # session deleted while queued
            run.status, run.started_at = "running", utcnow()
            concept, session_id, corr, image_ids = run.concept, run.session_id, run.correlation_id, list(run.image_ids)
            extract = run.extract
            images = {i.id: i for i in s.scalars(select(ImageRow).where(ImageRow.id.in_(image_ids))).all()}
        budget = self.budget_for(session_id, self.settings.max_live_requests_per_run,
                                 self.settings.max_live_usd_per_run)
        self.event(run_id, "run", "started", f"inspecting {len(image_ids)} image(s) for '{concept}' "
                                             f"[{self.settings.mode.upper()} mode]")
        failures, detections = 0, []
        try:
            for iid in image_ids:
                img = images[iid]
                image_input = ImageInput(Path(img.stored_path).read_bytes(), img.media_type, img.width, img.height,
                                         img.sha256)
                dets = self._segment(run_id, session_id, corr, img, image_input, concept, budget)
                if dets is None:
                    failures += 1
                    continue
                if extract:
                    failures += self._extract_all(run_id, session_id, corr, image_input, dets, concept, budget)
                detections.extend(dets)
        except BudgetExceeded as exc:
            self.event(run_id, "run", "error", f"stopped: {exc}")
            self._finish(run_id, "partial" if detections else "failed", f"BUDGET_EXCEEDED: {exc}")
            return
        self.event(run_id, "reconcile", "done", "reconciliation is recomputed deterministically on read")
        status = "succeeded" if failures == 0 else ("partial" if detections else "failed")
        self.event(run_id, "run", "done", f"{len(detections)} detection(s); {failures} failed step(s)")
        self._finish(run_id, status, None if failures == 0 else f"{failures} step(s) failed; see events")

    def _full_frame(self, run_id, img, concept):  # noqa: ANN001, ANN202
        """User-declared region = whole photo. No model call, no cost; recorded as a human choice, not SAM output."""
        w, h = img.width, img.height
        mask = {"bounds": [0, 0, w, h], "raster_w": w, "raster_h": h, "svg_path": f"M0 0H{w}V{h}H0Z",
                "area_px": w * h, "encoding": "full_frame"}
        with self.db.session() as s:
            row = DetectionRow(id=new_id("det"), run_id=run_id, image_id=img.id, concept=concept, object_index=1,
                               mask=mask, confidence=None, provider="full-frame", model="user-declared-region",
                               mode=self.settings.mode, provider_call_id=None)
            s.add(row)
        self.event(run_id, "segment", "done", f"{img.filename}: whole image declared as one region by the auditor "
                                              "(SAM not called)", image_id=img.id)
        return [row]

    def _segment(self, run_id, session_id, corr, img, image_input, concept, budget):  # noqa: ANN001, ANN202
        if run_id in self.full_frame_runs:
            return self._full_frame(run_id, img, concept)
        self.event(run_id, "segment", "started", f"segmenting {img.filename}", image_id=img.id)
        budget.reserve(SAM_USD_PER_IMAGE)
        started_at, t0 = utcnow(), time.perf_counter()
        try:
            result = self.seg.segment_image(image_input, concept)
        except ProviderError as exc:
            latency = (time.perf_counter() - t0) * 1000
            self.record_call(session_id=session_id, run_id=run_id, operation="segment", meta=None,
                             status="timeout" if exc.kind == "timeout" else
                             ("invalid_output" if exc.kind == "invalid_output" else "error"),
                             error=f"{exc.kind}: {exc.message}", correlation_id=corr, provider=self.seg, raw=exc.raw,
                             latency_ms=latency, started_at=started_at)
            self.event(run_id, "segment", "error", f"{img.filename}: {exc.message}", image_id=img.id,
                       latency_ms=latency)
            return None
        call_id = self.record_call(session_id=session_id, run_id=run_id, operation="segment", meta=result.meta,
                                   status="ok", error=None, correlation_id=corr, provider=self.seg,
                                   started_at=started_at)
        rows = []
        with self.db.session() as s:
            for obj in result.objects:
                row = DetectionRow(id=new_id("det"), run_id=run_id, image_id=img.id, concept=concept,
                                   object_index=obj.object_index, mask=obj.mask.as_dict(), confidence=obj.confidence,
                                   provider=self.seg.name, model=self.seg.model, mode=self.settings.mode,
                                   provider_call_id=call_id)
                s.add(row)
                rows.append(row)
        msg = f"{img.filename}: {len(rows)} match(es)" if rows else f"{img.filename}: zero matches (valid outcome)"
        self.event(run_id, "segment", "done", msg, image_id=img.id, latency_ms=round(result.meta.latency_ms, 2))
        return rows

    def _confirm(self, run_id, session_id, corr, image_input, crop_box, context, budget) -> dict:  # noqa: ANN001
        """Second, independently constructed read for the Tier 1 gate. A failure is recorded (and a run event
        written by the caller), never raised: without an agreeing second read the decision cannot reach Tier 1."""
        started_at = utcnow()
        record = {"view": CONFIRM_VIEW, "provider": self.ext.name, "model": self.ext.model, "created_at": started_at,
                  "evidence": None, "error": None, "provider_call_id": None, "view_ref": None}
        try:
            view = make_confirm_view(image_input, crop_box)
        except Exception as exc:  # no provider call was made: nothing to bill or record as a call
            record.update(status="error", error=f"could not build the enhanced view ({type(exc).__name__})")
            return record
        t0 = time.perf_counter()
        try:
            budget.reserve(EST_EXTRACT_USD)
            result = self.ext.extract_visual_evidence(view, context, purpose="confirm")
            budget.settle(EST_EXTRACT_USD, result.meta.estimated_cost_usd if result.meta.input_tokens else None)
        except BudgetExceeded:
            record.update(status="error", error="run budget reached before the second read")
            return record
        except Exception as raw_exc:
            exc = raw_exc if isinstance(raw_exc, ProviderError) else ProviderError(
                "error", f"unexpected {type(raw_exc).__name__} during second read")
            status = {"timeout": "timeout", "invalid_output": "invalid_output"}.get(exc.kind, "error")
            record["provider_call_id"] = self.record_call(
                session_id=session_id, run_id=run_id, operation="confirm", meta=None, status=status,
                error=f"{exc.kind}: {exc.message}", correlation_id=corr, provider=self.ext, raw=exc.raw,
                latency_ms=(time.perf_counter() - t0) * 1000, started_at=started_at)
            record.update(status="invalid" if exc.kind == "invalid_output" else "error", error=exc.message)
            return record
        call_id = self.record_call(session_id=session_id, run_id=run_id, operation="confirm",
                                   meta=result.meta, status="ok", error=None, correlation_id=corr, provider=self.ext,
                                   started_at=started_at)
        view_path = self.raw_dir / f"{call_id}.view.jpg"
        view_path.write_bytes(view.data)
        record.update(status="ok", evidence=result.evidence.model_dump(mode="json"), provider_call_id=call_id,
                      view_ref=str(view_path.relative_to(self.settings.data_dir)))
        return record

    def _extract_all(self, run_id, session_id, corr, image_input, dets, concept, budget) -> int:  # noqa: ANN001
        with ThreadPoolExecutor(max_workers=self.settings.provider_concurrency) as pool:
            results = list(pool.map(
                lambda d: self._extract(run_id, session_id, corr, image_input, d, concept, budget), dets))
        return sum(1 for ok in results if not ok)

    def _extract(self, run_id, session_id, corr, image_input, det, concept, budget) -> bool:  # noqa: ANN001
        started_at, t0 = utcnow(), time.perf_counter()
        try:
            crop, crop_box = make_crop(image_input, tuple(det.mask["bounds"]))
            ref = EvidenceReference(detection_id=det.id, image_id=det.image_id, image_sha256=image_input.sha256,
                                    crop_box=crop_box)
            context = CropContext(image_input.sha256, det.object_index, crop_box, concept)
            budget.reserve(EST_EXTRACT_USD)
            t0 = time.perf_counter()
            result = self.ext.extract_visual_evidence(crop, context)
            budget.settle(EST_EXTRACT_USD, result.meta.estimated_cost_usd if result.meta.input_tokens else None)
        except BudgetExceeded:
            raise
        except Exception as raw_exc:  # one bad detection must never fail the run or drop sibling evidence
            exc = raw_exc if isinstance(raw_exc, ProviderError) else ProviderError(
                "error", f"unexpected {type(raw_exc).__name__} during extraction")
            if not isinstance(raw_exc, ProviderError):
                log.exception("extraction crashed for %s", det.id)
            latency = (time.perf_counter() - t0) * 1000
            status = {"timeout": "timeout", "invalid_output": "invalid_output"}.get(exc.kind, "error")
            call_id = self.record_call(session_id=session_id, run_id=run_id, operation="extract", meta=None,
                                       status=status, error=f"{exc.kind}: {exc.message}", correlation_id=corr,
                                       provider=self.ext, raw=exc.raw, latency_ms=latency, started_at=started_at)
            with self.db.session() as s:
                s.add(EvidenceRow(id=new_id("ev"), detection_id=det.id,
                                  status="invalid" if exc.kind == "invalid_output" else "error", evidence=None,
                                  error=exc.message, provider=self.ext.name, model=self.ext.model,
                                  mode=self.settings.mode, provider_call_id=call_id))
            self.event(run_id, "extract", "error", f"object #{det.object_index}: {exc.message}",
                       image_id=det.image_id, detection_id=det.id, latency_ms=round(latency, 2))
            return False
        call_id = self.record_call(session_id=session_id, run_id=run_id, operation="extract", meta=result.meta,
                                   status="ok", error=None, correlation_id=corr, provider=self.ext,
                                   started_at=started_at)
        evidence = VisualEvidence(**result.evidence.model_dump(), evidence_references=[ref])
        confirmation = None
        if needs_confirmation(result.evidence):
            confirmation = self._confirm(run_id, session_id, corr, image_input, crop_box, context, budget)
            if confirmation["status"] != "ok":
                self.event(run_id, "extract", "error", f"object #{det.object_index}: second read "
                           f"{confirmation['status']} ({confirmation['error']}); Tier 1 withheld",
                           image_id=det.image_id, detection_id=det.id)
        with self.db.session() as s:
            s.add(EvidenceRow(id=new_id("ev"), detection_id=det.id, status="ok", evidence=evidence.model_dump(mode="json"),
                              error=None, provider=self.ext.name, model=self.ext.model, mode=self.settings.mode,
                              provider_call_id=call_id, confirmation=confirmation))
        self.event(run_id, "extract", "done", f"object #{det.object_index}: evidence validated",
                   image_id=det.image_id, detection_id=det.id, latency_ms=round(result.meta.latency_ms, 2))
        return confirmation is None or confirmation["status"] == "ok"  # a failed second read is a failed step
