"""Runtime configuration from environment variables. Secrets are read here and never serialized."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

VERSION = "0.1.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Verified against https://dev.meta.ai/docs/models (2026-10-31).
META_BASE_URL = "https://api.meta.ai/v1"
SAM_MODEL_ID = "sam-3.1"
MUSE_MODEL_ID = "muse-spark-1.3"

# https://dev.meta.ai/docs/pricing-rate-limits (2026-10-31), Standard mode.
SAM_USD_PER_IMAGE = 2.50 / 1000
MUSE_USD_PER_INPUT_TOKEN = 1.25 / 1_000_000
MUSE_USD_PER_OUTPUT_TOKEN = 4.25 / 1_000_000


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class Settings:
    mode: str = "demo"
    data_dir: Path = PROJECT_ROOT / "backend" / "data"
    fixtures_dir: Path = PROJECT_ROOT / "fixtures"
    database_url: str = ""
    live_approved: bool = False
    max_upload_mb: int = 15
    max_ledger_mb: int = 2
    max_images_per_session: int = 20
    max_ledger_rows: int = 5000
    max_live_requests_per_run: int = 40
    max_live_usd_per_run: float = 0.50
    max_live_requests_per_session: int = 12
    max_live_usd_total: float = 1.00
    provider_timeout_s: float = 60.0
    provider_max_retries: int = 2
    provider_concurrency: int = 2
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")
    access_code: str = field(default="", repr=False)  # hosted demo gate; empty = local, no gate
    _api_key: str = field(default="", repr=False)

    @property
    def credentials_present(self) -> bool:
        return bool(self._api_key)

    @property
    def live_ready(self) -> bool:
        return self.mode == "live" and self.live_approved and self.credentials_present

    def api_key(self) -> str:
        return self._api_key


def load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    """Minimal KEY=VALUE loader. Real environment variables always win over the file."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


MIN_ACCESS_CODE_LEN = 24


def _access_code() -> str:
    code = os.environ.get("AUDITGLIMMER_ACCESS_CODE", "").strip()
    if code and len(code) < MIN_ACCESS_CODE_LEN:
        raise ValueError(f"AUDITGLIMMER_ACCESS_CODE must be at least {MIN_ACCESS_CODE_LEN} characters")
    return code


def load_settings() -> Settings:
    load_dotenv()
    mode = os.environ.get("AUDITGLIMMER_MODE", "demo").strip().lower()
    if mode not in {"demo", "live"}:
        raise ValueError(f"AUDITGLIMMER_MODE must be 'demo' or 'live', got {mode!r}")
    data_dir = Path(os.environ.get("AUDITGLIMMER_DATA_DIR", PROJECT_ROOT / "backend" / "data"))
    database_url = os.environ.get("AUDITGLIMMER_DATABASE_URL", f"sqlite:///{data_dir / 'auditglimmer.db'}")
    return Settings(
        mode=mode,
        data_dir=data_dir,
        database_url=database_url,
        live_approved=_flag("AUDITGLIMMER_LIVE_APPROVED"),
        max_images_per_session=int(os.environ.get("AUDITGLIMMER_MAX_IMAGES_PER_SESSION", "20")),
        max_live_requests_per_run=int(os.environ.get("AUDITGLIMMER_MAX_LIVE_REQUESTS_PER_RUN", "40")),
        max_live_usd_per_run=float(os.environ.get("AUDITGLIMMER_MAX_LIVE_USD_PER_RUN", "0.50")),
        max_live_requests_per_session=int(os.environ.get("AUDITGLIMMER_MAX_LIVE_REQUESTS_PER_SESSION", "12")),
        max_live_usd_total=float(os.environ.get("AUDITGLIMMER_MAX_LIVE_USD_TOTAL", "1.00")),
        cors_origins=tuple(o.strip() for o in os.environ.get("AUDITGLIMMER_CORS_ORIGINS", "").split(",") if o.strip())
        or Settings.cors_origins,
        access_code=_access_code(),
        _api_key=os.environ.get("MODEL_API_KEY", ""),
    )
