"""FastAPI application: routes are thin; logic lives in services, pipeline, reconcile, report."""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import shutil
import threading
import time
import uuid
from contextvars import ContextVar
from pathlib import Path

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from sqlalchemy import delete, select

from .config import MUSE_MODEL_ID, SAM_MODEL_ID, VERSION, Settings, load_settings
from .db import AuditSession, Database, DetectionRow, ImageRow, LedgerRow, ProviderCallRow, ReviewRow, RunEventRow, RunRow, new_id, utcnow
from .errors import ApiError, ProviderError
from .ledger import parse_ledger
from .reconcile import TYPE_SYNONYMS, canonical_type
from .pipeline import BudgetExceeded, Pipeline
from .providers.factory import build_providers
from .report import build_report, report_csv, report_html
from .schemas import (
    ConfigInfo, DetectionOut, LedgerIssue, EvidenceGraphOut, EvidenceRecordOut, ImageOut, LedgerRecordOut, LedgerUploadResult,
    MatchDecisionOut, OverviewOut, ReconciliationOut, ReviewCreate, RunCreate, RunOut, SessionCreate, SessionOut,
    TraceOut,
)
from .security import sanitize_filename, validate_image
from .services import (
    REVIEW_LOCK, apply_review, build_graph, build_overview, build_reconciliation, build_trace, detection_out, event_out, latest_detections,
    evidence_out, find_decision, get_session_or_404, image_out, ledger_out, run_out, session_out,
)

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"ts": self.formatTime(record), "level": record.levelname, "logger": record.name,
                   "msg": record.getMessage(), "correlation_id": correlation_id.get()}
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info).splitlines()[-1]
        return json.dumps(payload)


def _configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("auditglimmer")
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    root.propagate = False


log = logging.getLogger("auditglimmer.api")
SSE_POLL_S = 0.25
MAX_ACTIVE_RUNS = 4
MAX_LIVE_EXPLAINS_PER_PROCESS = 20
SSE_MAX_S = 600
# ponytail: process-wide lock makes check-then-insert atomic for one uvicorn worker; multi-worker needs a DB constraint
_RUN_CREATE_LOCK = threading.Lock()


def _err(status: int, code: str, message: str, details: list | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {
        "code": code, "message": message, "details": details or [], "correlation_id": correlation_id.get()}})


def create_app(settings: Settings | None = None) -> FastAPI:  # noqa: C901 - route table
    settings = settings or load_settings()
    _configure_logging()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    database = Database(settings.database_url)
    seg, ext = build_providers(settings)
    pipeline = Pipeline(settings, database, seg, ext)
    with database.session() as db:  # runs orphaned by a previous process can never finish
        for stale in db.scalars(select(RunRow).where(RunRow.status.in_(("queued", "running")))).all():
            stale.status, stale.error = "failed", "interrupted: server restarted before the run finished"
    explain_calls = {"count": 0}
    app = FastAPI(title="AuditGlimmer API", version=VERSION)
    app.state.settings, app.state.db, app.state.pipeline = settings, database, pipeline
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"],
                       allow_headers=["*"], expose_headers=["X-Correlation-ID", "Content-Disposition"])

    @app.middleware("http")
    async def access_gate(request: Request, call_next):  # noqa: ANN001, ANN202
        """Hosted demo gate. Off when no code is configured (local use)."""
        path = request.url.path
        if not settings.access_code or request.method == "OPTIONS" or not path.startswith("/api/") \
                or path == "/api/health":
            return await call_next(request)
        supplied = request.headers.get("x-access-code", "")
        header_less = path.startswith("/api/images/") or (path.startswith("/api/runs/") and path.endswith("/events"))
        if not supplied and header_less:  # <img src> and EventSource cannot send headers
            supplied = request.query_params.get("access_code", "")
        if not hmac.compare_digest(supplied.encode(), settings.access_code.encode()):
            return _err(401, "UNAUTHORIZED", "a valid access code is required for this demo")
        return await call_next(request)

    @app.middleware("http")
    async def correlation(request: Request, call_next):  # noqa: ANN001, ANN202
        cid = request.headers.get("x-correlation-id", "")[:64] or uuid.uuid4().hex[:16]
        if not all(c.isalnum() or c in "-_" for c in cid):
            cid = uuid.uuid4().hex[:16]
        token = correlation_id.set(cid)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # unhandled: answer here so the envelope and header keep the correlation id
            log.exception("unhandled error")
            response = _err(500, "INTERNAL", "internal server error")
        finally:
            correlation_id.reset(token)
        response.headers["X-Correlation-ID"] = cid
        response.headers["X-Content-Type-Options"] = "nosniff"
        log.info(json.dumps({"method": request.method, "path": request.url.path, "status": response.status_code,
                             "ms": round((time.perf_counter() - started) * 1000, 1), "cid": cid}))
        return response

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _err(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "issue": e["msg"]} for e in exc.errors()]
        return _err(422, "VALIDATION_FAILED", "request validation failed", details)

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error")
        return _err(500, "INTERNAL", "internal server error")

    def session_dir(sid: str) -> Path:
        return settings.data_dir / "sessions" / sid

    # ---------- meta ----------
    @app.get("/api/health")
    def health() -> dict:
        s_ok, s_detail = seg.health_check()
        e_ok, e_detail = ext.health_check()
        return {"status": "ok", "mode": settings.mode, "providers": {
            "segmentation": {"ok": s_ok, "detail": s_detail}, "extraction": {"ok": e_ok, "detail": e_detail}}}

    @app.get("/api/config", response_model=ConfigInfo)
    def config() -> ConfigInfo:
        live = settings.mode == "live"
        return ConfigInfo(mode=settings.mode, live_approved=settings.live_ready,
                          credentials_present=settings.credentials_present,
                          segmentation_model=SAM_MODEL_ID if live else "fixture-sam",
                          extraction_model=MUSE_MODEL_ID if live else "fixture-muse",
                          max_live_requests_per_run=settings.max_live_requests_per_run,
                          max_upload_mb=settings.max_upload_mb, version=VERSION)

    @app.get("/api/overview", response_model=OverviewOut)
    def overview() -> OverviewOut:
        with database.session() as db:
            return build_overview(db, settings.mode)

    # ---------- sessions ----------
    @app.get("/api/sessions", response_model=list[SessionOut])
    def list_sessions() -> list[SessionOut]:
        with database.session() as db:
            rows = db.scalars(select(AuditSession).order_by(AuditSession.created_at.desc())).all()
            return [session_out(db, r) for r in rows]

    @app.post("/api/sessions", response_model=SessionOut, status_code=201)
    def create_session(body: SessionCreate) -> SessionOut:
        with database.session() as db:
            row = AuditSession(id=new_id("ses"), name=body.name.strip(), facility_id=body.facility_id)
            db.add(row)
            db.flush()
            return session_out(db, row)

    @app.get("/api/sessions/{sid}", response_model=SessionOut)
    def get_session(sid: str) -> SessionOut:
        with database.session() as db:
            return session_out(db, get_session_or_404(db, sid))

    @app.delete("/api/sessions/{sid}", status_code=204)
    def delete_session(sid: str) -> Response:
        with database.session() as db:
            row = get_session_or_404(db, sid)
            raw_refs = [r for r in db.scalars(select(ProviderCallRow.raw_output_ref)
                                              .where(ProviderCallRow.session_id == sid)).all() if r]
            db.delete(row)
        shutil.rmtree(session_dir(sid), ignore_errors=True)
        data_root = settings.data_dir.resolve()
        for ref in raw_refs:  # raw provider outputs are part of the session's retained data
            path = (settings.data_dir / ref).resolve()
            if path.is_relative_to(data_root):
                path.unlink(missing_ok=True)
        return Response(status_code=204)

    # ---------- ledger ----------
    def _archive_reviews(sid: str, reviews: list[ReviewRow]) -> None:
        """Reviews are audit records: a register replacement archives them to disk, never silently drops them."""
        target = session_dir(sid) / "review-archive" / f"{utcnow().replace(':', '')}-{uuid.uuid4().hex[:6]}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps([{"id": r.id, "decision_id": r.decision_id, "evidence_id": r.evidence_id,
                                       "action": r.action, "asset_id": r.asset_id, "reviewer": r.reviewer,
                                       "note": r.note, "created_at": r.created_at} for r in reviews], indent=2))

    def _store_ledger(sid: str, data: bytes, replace: bool) -> LedgerUploadResult:
        parsed = parse_ledger(data, settings.max_ledger_rows, settings.max_ledger_mb * 1024 * 1024)
        if not parsed.rows:
            raise ApiError(400, "LEDGER_EMPTY", f"no ledger rows were accepted ({parsed.rejected} rejected); "
                                                "the current register and reviews are unchanged",
                           [i.model_dump() for i in parsed.issues[:50]])
        with database.session() as db:
            session = get_session_or_404(db, sid)
            reviews = db.scalars(select(ReviewRow).where(ReviewRow.session_id == sid)
                                 .order_by(ReviewRow.created_at, ReviewRow.id)).all()
            if reviews and not replace:
                raise ApiError(409, "LEDGER_HAS_REVIEWS", f"this session has {len(reviews)} human review(s) tied to "
                                                          "the current register; re-send with replace=true to "
                                                          "archive them and load the new register")
            if reviews:
                _archive_reviews(sid, reviews)
            db.execute(delete(LedgerRow).where(LedgerRow.session_id == sid))
            # reviews reference asset_id strings of the old register; a new register voids them (archived above)
            db.execute(delete(ReviewRow).where(ReviewRow.session_id == sid))
            rows = [LedgerRow(id=new_id("led"), session_id=sid, **r) for r in parsed.rows]
            issues = parsed.issues + [
                LedgerIssue(row=r["source_row"], field="facility_id", severity="warning", code="FACILITY_MISMATCH",
                            message=f"asset is at {r['facility_id']}, not this session's facility "
                                    f"{session.facility_id}; it cannot be matched by this session's photos")
                for r in parsed.rows if r["facility_id"] != session.facility_id]
            db.add_all(rows)
            session.ledger_sha256 = parsed.sha256
            db.flush()
            return LedgerUploadResult(accepted=len(rows), rejected=parsed.rejected, issues=issues,
                                      file_sha256=parsed.sha256, records=[ledger_out(r) for r in rows],
                                      archived_reviews=len(reviews))

    @app.post("/api/sessions/{sid}/ledger", response_model=LedgerUploadResult)
    def upload_ledger(sid: str, file: UploadFile = File(...), replace: bool = False) -> LedgerUploadResult:
        if not (file.filename or "").lower().endswith(".csv"):
            raise ApiError(415, "UNSUPPORTED_MEDIA", "ledger must be a .csv file")
        data = file.file.read(settings.max_ledger_mb * 1024 * 1024 + 1)
        return _store_ledger(sid, data, replace)

    @app.get("/api/sessions/{sid}/ledger", response_model=list[LedgerRecordOut])
    def get_ledger(sid: str) -> list[LedgerRecordOut]:
        with database.session() as db:
            get_session_or_404(db, sid)
            rows = db.scalars(select(LedgerRow).where(LedgerRow.session_id == sid).order_by(LedgerRow.source_row)).all()
            return [ledger_out(r) for r in rows]

    # ---------- images ----------
    def _store_image(sid: str, filename: str, data: bytes, facility_id: str, fixture: bool) -> ImageOut:
        img = validate_image(data, settings.max_upload_mb * 1024 * 1024)
        with database.session() as db:
            get_session_or_404(db, sid)
            count = len(db.scalars(select(ImageRow.id).where(ImageRow.session_id == sid)).all())
            if count >= settings.max_images_per_session:
                raise ApiError(400, "VALIDATION_FAILED", f"max {settings.max_images_per_session} images per session")
            existing = db.scalar(select(ImageRow).where(ImageRow.session_id == sid, ImageRow.sha256 == img.sha256))
            if existing:
                return image_out(existing)
            iid = new_id("img")
            target = session_dir(sid) / "images" / f"{iid}.{img.extension}"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(img.data)
            row = ImageRow(id=iid, session_id=sid, filename=sanitize_filename(filename, f"{iid}.{img.extension}"),
                           stored_path=str(target), sha256=img.sha256, width=img.width, height=img.height,
                           media_type=img.media_type, facility_id=facility_id, fixture=fixture)
            db.add(row)
            db.flush()
            return image_out(row)

    @app.post("/api/sessions/{sid}/images", response_model=list[ImageOut])
    def upload_images(sid: str, files: list[UploadFile] = File(...)) -> list[ImageOut]:
        with database.session() as db:
            facility = get_session_or_404(db, sid).facility_id
        if len(files) > settings.max_images_per_session:
            raise ApiError(400, "VALIDATION_FAILED", f"max {settings.max_images_per_session} images per upload")
        out = []
        for f in files:
            data = f.file.read(settings.max_upload_mb * 1024 * 1024 + 1)
            out.append(_store_image(sid, f.filename or "image", data, facility, fixture=False))
        return out

    @app.get("/api/sessions/{sid}/images", response_model=list[ImageOut])
    def list_images(sid: str) -> list[ImageOut]:
        with database.session() as db:
            get_session_or_404(db, sid)
            rows = db.scalars(select(ImageRow).where(ImageRow.session_id == sid).order_by(ImageRow.uploaded_at)).all()
            return [image_out(r) for r in rows]

    @app.get("/api/images/{iid}/file")
    def image_file(iid: str) -> FileResponse:
        with database.session() as db:
            row = db.get(ImageRow, iid)
            if row is None:
                raise ApiError(404, "NOT_FOUND", "image not found")
            path, media = Path(row.stored_path), row.media_type
        if not path.resolve().is_relative_to(settings.data_dir.resolve()):
            raise ApiError(404, "NOT_FOUND", "image not found")
        return FileResponse(path, media_type=media, headers={"Cache-Control": "private, max-age=3600"})

    @app.post("/api/sessions/{sid}/demo")
    def load_demo(sid: str, replace: bool = False) -> dict:
        if settings.mode != "demo":
            raise ApiError(403, "LIVE_NOT_APPROVED", "demo dataset is only available in DEMO mode")
        manifest = json.loads((settings.fixtures_dir / "manifest.json").read_text())
        ledger = _store_ledger(sid, (settings.fixtures_dir / "ledger.csv").read_bytes(), replace)
        images = [_store_image(sid, m["file"], (settings.fixtures_dir / "images" / m["file"]).read_bytes(),
                               m["facility_id"], fixture=True) for m in manifest["images"]]
        return {"ledger": ledger.model_dump(), "images": [i.model_dump() for i in images]}

    # ---------- runs ----------
    @app.post("/api/sessions/{sid}/runs", response_model=RunOut, status_code=202)
    def create_run(sid: str, body: RunCreate) -> RunOut:
        if settings.mode == "live" and not settings.live_ready:
            raise ApiError(403, "LIVE_NOT_APPROVED", "LIVE mode requires MODEL_API_KEY and AUDITGLIMMER_LIVE_APPROVED=1; "
                                                     "no mock fallback is used")
        concept = canonical_type(body.concept)
        supported = sorted(set(TYPE_SYNONYMS.values()))
        if concept not in supported:
            raise ApiError(400, "VALIDATION_FAILED", f"unsupported asset concept {body.concept!r}; "
                                                     f"use one of: {', '.join(supported)}")
        with _RUN_CREATE_LOCK, database.session() as db:
            get_session_or_404(db, sid)
            if db.scalar(select(RunRow.id).where(RunRow.session_id == sid,
                                                 RunRow.status.in_(("queued", "running"))).limit(1)):
                raise ApiError(409, "RUN_IN_PROGRESS", "an inspection is already running for this session; "
                                                       "wait for it to finish")
            active = len(db.scalars(select(RunRow.id).where(RunRow.status.in_(("queued", "running")))).all())
            if active >= MAX_ACTIVE_RUNS:
                raise ApiError(429, "BUDGET_EXCEEDED", f"{active} runs already queued or running; retry when one finishes")
            all_ids = [i.id for i in db.scalars(select(ImageRow).where(ImageRow.session_id == sid)
                                                .order_by(ImageRow.uploaded_at)).all()]
            ids = body.image_ids or all_ids
            unknown = [i for i in ids if i not in all_ids]
            if unknown:
                raise ApiError(400, "VALIDATION_FAILED", "unknown image ids for this session", unknown)
            if not ids:
                raise ApiError(400, "VALIDATION_FAILED", "upload at least one image before running an inspection")
            run = RunRow(id=new_id("run"), session_id=sid, concept=concept, status="queued", image_ids=ids,
                         mode=settings.mode, extract=body.extract, correlation_id=correlation_id.get())
            db.add(run)
            db.flush()
            out = run_out(db, run)
        if body.region == "full_frame":
            pipeline.full_frame_runs.add(out.id)
        pipeline.start(out.id)
        return out

    @app.get("/api/runs/{rid}", response_model=RunOut)
    def get_run(rid: str) -> RunOut:
        with database.session() as db:
            run = db.get(RunRow, rid)
            if run is None:
                raise ApiError(404, "NOT_FOUND", "run not found")
            return run_out(db, run)

    def _poll(rid: str, after: int) -> tuple[list[dict], str | None]:
        with database.session() as db:
            run = db.get(RunRow, rid)
            if run is None:
                return [], "missing"
            rows = db.scalars(select(RunEventRow).where(RunEventRow.run_id == rid, RunEventRow.seq > after)
                              .order_by(RunEventRow.seq)).all()
            return [event_out(e).model_dump() for e in rows], run.status

    @app.get("/api/runs/{rid}/events")
    async def run_events(rid: str) -> StreamingResponse:
        _, status = await asyncio.to_thread(_poll, rid, 10**9)
        if status == "missing":
            raise ApiError(404, "NOT_FOUND", "run not found")

        async def stream():  # noqa: ANN202
            last, deadline = 0, time.monotonic() + SSE_MAX_S
            while time.monotonic() < deadline:
                events, status = await asyncio.to_thread(_poll, rid, last)
                for ev in events:
                    last = ev["seq"]
                    yield f"id: {last}\ndata: {json.dumps(ev)}\n\n"
                if status == "missing":
                    yield f"event: end\ndata: {json.dumps({'status': 'deleted'})}\n\n"
                    return
                if status in {"succeeded", "partial", "failed"} and not events:
                    yield f"event: end\ndata: {json.dumps({'status': status})}\n\n"
                    return
                await asyncio.sleep(SSE_POLL_S)
            yield "event: end\ndata: {\"status\": \"stream_timeout\"}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # ---------- results ----------
    @app.get("/api/sessions/{sid}/detections")
    def detections(sid: str, image_id: str | None = Query(default=None)) -> list[dict]:
        with database.session() as db:
            recon, det_by_ev = build_reconciliation(db, sid)
            by_det = {d.detection_id: d for d in recon.decisions}

            out = []
            for det in latest_detections(db, sid):
                if image_id and det.image_id != image_id:
                    continue
                out.append({
                    "detection": DetectionOut.model_validate(detection_out(det)).model_dump(mode="json"),
                    "evidence": EvidenceRecordOut.model_validate(evidence_out(det.evidence)).model_dump(mode="json")
                    if det.evidence else None,
                    "decision": MatchDecisionOut.model_validate(by_det[det.id]).model_dump(mode="json")
                    if det.id in by_det else None})
            return out

    @app.post("/api/detections/{did}/extract")
    def extract_detection(did: str) -> dict:
        """Run evidence extraction for ONE user-selected region (one provider call in LIVE)."""
        if settings.mode == "live" and not settings.live_ready:
            raise ApiError(403, "LIVE_NOT_APPROVED", "LIVE extraction requires MODEL_API_KEY and approval")
        try:
            pipeline.extract_one(did)
        except LookupError as exc:
            raise ApiError(404, "NOT_FOUND", "detection not found") from exc
        except FileExistsError as exc:
            raise ApiError(409, "CONFLICT", "evidence already extracted for this region") from exc
        except BudgetExceeded as exc:
            raise ApiError(429, "BUDGET_EXCEEDED", str(exc)) from exc
        with database.session() as db:
            det = db.get(DetectionRow, did)
            sid = db.get(RunRow, det.run_id).session_id
            recon, _ = build_reconciliation(db, sid)
            decision = next((d for d in recon.decisions if d.detection_id == did), None)
            return {"detection": detection_out(det).model_dump(mode="json"),
                    "evidence": evidence_out(det.evidence).model_dump(mode="json") if det.evidence else None,
                    "decision": decision.model_dump(mode="json") if decision else None}

    @app.get("/api/sessions/{sid}/reconciliation", response_model=ReconciliationOut)
    def reconciliation(sid: str) -> ReconciliationOut:
        with database.session() as db:
            return build_reconciliation(db, sid)[0]

    @app.get("/api/sessions/{sid}/review-queue", response_model=list[MatchDecisionOut])
    def review_queue(sid: str) -> list[MatchDecisionOut]:
        with database.session() as db:
            recon, _ = build_reconciliation(db, sid)
            return [d for d in recon.decisions if d.review_required and d.review is None]

    @app.post("/api/decisions/{did}/review", response_model=MatchDecisionOut)
    def review(did: str, body: ReviewCreate) -> MatchDecisionOut:
        with REVIEW_LOCK, database.session() as db:  # lock spans validation and commit
            return apply_review(db, did, body)

    @app.post("/api/decisions/{did}/explain")
    def explain(did: str) -> dict:
        with database.session() as db:
            sid, dec, _ = find_decision(db, did)
        facts = [f"decision={dec.decision}", f"rule={dec.matching_rule}", f"candidates={dec.candidate_asset_ids}",
                 f"flags={dec.flags}", f"unmatched_fields={dec.unmatched_fields}", dec.explanation]
        if settings.mode == "live" and not settings.live_ready:
            raise ApiError(403, "LIVE_NOT_APPROVED", "LIVE explanation requires approval")
        if settings.mode == "live":
            if explain_calls["count"] >= MAX_LIVE_EXPLAINS_PER_PROCESS:
                raise ApiError(429, "BUDGET_EXCEEDED", "live explanation cap reached for this server process")
            explain_calls["count"] += 1
        started_at, t0 = utcnow(), time.perf_counter()
        try:
            text, meta = ext.explain_discrepancy(facts)
        except ProviderError as exc:
            pipeline.record_call(session_id=sid, run_id=None, operation="explain", meta=None,
                                 status="timeout" if exc.kind == "timeout" else "error",
                                 error=f"{exc.kind}: {exc.message}", correlation_id=correlation_id.get(),
                                 provider=ext, raw=exc.raw, latency_ms=(time.perf_counter() - t0) * 1000,
                                 started_at=started_at)
            raise ApiError(504 if exc.kind == "timeout" else 502,
                           "PROVIDER_TIMEOUT" if exc.kind == "timeout" else "PROVIDER_ERROR", exc.message) from exc
        meta.latency_ms = meta.latency_ms or (time.perf_counter() - t0) * 1000
        pipeline.record_call(session_id=sid, run_id=None, operation="explain", meta=meta, status="ok", error=None,
                             correlation_id=correlation_id.get(), provider=ext, started_at=started_at)
        return {"explanation": text, "grounded_facts": facts, "provider": ext.name, "mode": settings.mode}

    @app.get("/api/sessions/{sid}/report")
    def report(sid: str, format: str = Query(default="json", pattern="^(json|html|csv)$"),  # noqa: A002
               download: bool = False) -> Response:
        with database.session() as db:
            data = build_report(db, sid, settings, mark_reported=download)
        stamp = data["generated_at"][:19].replace(":", "")
        if format == "html":
            disposition = "attachment" if download else "inline"
            return HTMLResponse(report_html(data), headers={
                "Content-Disposition": f'{disposition}; filename="auditglimmer-{sid}-{stamp}.html"'})
        if format == "csv":
            return Response(report_csv(data), media_type="text/csv", headers={
                "Content-Disposition": f'attachment; filename="auditglimmer-{sid}-{stamp}.csv"'})
        return JSONResponse(data)

    @app.get("/api/sessions/{sid}/trace", response_model=TraceOut)
    def trace(sid: str) -> TraceOut:
        with database.session() as db:
            return build_trace(db, sid)

    @app.get("/api/sessions/{sid}/evidence-graph", response_model=EvidenceGraphOut)
    def evidence_graph(sid: str) -> EvidenceGraphOut:
        with database.session() as db:
            return build_graph(db, sid)

    return app
