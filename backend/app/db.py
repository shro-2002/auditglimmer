"""SQLAlchemy persistence. Typed tables + foreign keys form the evidence-provenance graph (docs/ontology.md)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Base(DeclarativeBase):
    pass


class AuditSession(Base):
    __tablename__ = "audit_sessions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    facility_id: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
    ledger_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reported_at: Mapped[str | None] = mapped_column(String(32), nullable=True)

    ledger: Mapped[list[LedgerRow]] = relationship(cascade="all, delete-orphan", passive_deletes=True, back_populates="session")
    images: Mapped[list[ImageRow]] = relationship(cascade="all, delete-orphan", passive_deletes=True, back_populates="session")
    runs: Mapped[list[RunRow]] = relationship(cascade="all, delete-orphan", passive_deletes=True, back_populates="session")


class LedgerRow(Base):
    __tablename__ = "ledger_records"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("audit_sessions.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[str] = mapped_column(String(80))
    asset_type: Mapped[str] = mapped_column(String(80))
    manufacturer: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    facility_id: Mapped[str] = mapped_column(String(40))
    expected_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ledger_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    inspection_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_row: Mapped[int] = mapped_column(Integer)
    session: Mapped[AuditSession] = relationship(back_populates="ledger")


class ImageRow(Base):
    __tablename__ = "images"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("audit_sessions.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(200))
    stored_path: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    media_type: Mapped[str] = mapped_column(String(40))
    facility_id: Mapped[str] = mapped_column(String(40))
    uploaded_at: Mapped[str] = mapped_column(String(32), default=utcnow)
    fixture: Mapped[bool] = mapped_column(Boolean, default=False)
    session: Mapped[AuditSession] = relationship(back_populates="images")


class RunRow(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("audit_sessions.id", ondelete="CASCADE"), index=True)
    concept: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    image_ids: Mapped[list] = mapped_column(JSON, default=list)
    extract: Mapped[bool] = mapped_column(Boolean, default=True)
    mode: Mapped[str] = mapped_column(String(8))
    started_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(40))
    session: Mapped[AuditSession] = relationship(back_populates="runs")
    detections: Mapped[list[DetectionRow]] = relationship(cascade="all, delete-orphan", passive_deletes=True, back_populates="run")
    events: Mapped[list[RunEventRow]] = relationship(cascade="all, delete-orphan", passive_deletes=True, order_by="RunEventRow.seq")


class DetectionRow(Base):
    __tablename__ = "detections"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    image_id: Mapped[str] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    concept: Mapped[str] = mapped_column(String(60))
    object_index: Mapped[int] = mapped_column(Integer)
    mask: Mapped[dict] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(40))
    mode: Mapped[str] = mapped_column(String(8))
    provider_call_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    run: Mapped[RunRow] = relationship(back_populates="detections")
    evidence: Mapped[EvidenceRow | None] = relationship(cascade="all, delete-orphan", passive_deletes=True, uselist=False)


class EvidenceRow(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    detection_id: Mapped[str] = mapped_column(ForeignKey("detections.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(String(10))
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(40))
    mode: Mapped[str] = mapped_column(String(8))
    provider_call_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ReviewRow(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("audit_sessions.id", ondelete="CASCADE"), index=True)
    decision_id: Mapped[str] = mapped_column(String(64), index=True)
    evidence_id: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(8))
    asset_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reviewer: Mapped[str] = mapped_column(String(80))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)


class RunEventRow(Base):
    __tablename__ = "run_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    ts: Mapped[str] = mapped_column(String(32), default=utcnow)
    stage: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(10))
    message: Mapped[str] = mapped_column(Text)
    image_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    detection_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)


class ProviderCallRow(Base):
    __tablename__ = "provider_calls"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("audit_sessions.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(40))
    mode: Mapped[str] = mapped_column(String(8))
    operation: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(16))
    latency_ms: Mapped[float] = mapped_column(Float)
    started_at: Mapped[str] = mapped_column(String(32))
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    images: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_output_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(40))


class Database:
    def __init__(self, url: str) -> None:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(url, connect_args=connect_args)
        if url.startswith("sqlite"):
            event.listen(self.engine, "connect", _sqlite_pragmas)
        self._factory = sessionmaker(self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        db = self._factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def _sqlite_pragmas(dbapi_connection, _record) -> None:  # noqa: ANN001 - DBAPI hook signature
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()
