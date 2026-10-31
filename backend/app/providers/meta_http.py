"""Minimal Meta Model API HTTP transport: auth header, bounded retries, timeouts.

Behaviour follows https://dev.meta.ai/docs/error-handling (2026-10-31): 400/401/403/404 are
permanent; 429/500/503 retry with exponential backoff + jitter honouring Retry-After.
"""

from __future__ import annotations

import json
import random
import time
from collections.abc import Iterator
from contextlib import contextmanager

import httpx

from ..config import META_BASE_URL
from ..errors import ProviderError

RETRYABLE = {429, 500, 502, 503}
BACKOFF_START_S = 0.5
MAX_BACKOFF_S = 20.0


class MetaHttp:
    def __init__(self, api_key: str, timeout_s: float, max_retries: int, base_url: str = META_BASE_URL,
                 transport: httpx.BaseTransport | None = None, sleep=time.sleep) -> None:  # noqa: ANN001
        if not api_key:
            raise ProviderError("not_approved", "MODEL_API_KEY is not set")
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._timeout = httpx.Timeout(timeout_s, connect=10.0)
        self._retries = max_retries
        self._base = base_url.rstrip("/")
        self._transport = transport  # injectable for offline contract tests
        self._sleep = sleep

    def _sleep_for(self, attempt: int, response: httpx.Response | None) -> float:
        retry_after = response.headers.get("retry-after") if response is not None else None
        if retry_after and retry_after.isdigit():
            return min(float(retry_after), MAX_BACKOFF_S)
        return min(BACKOFF_START_S * 2**attempt, MAX_BACKOFF_S) * (0.5 + random.random())

    def post_json(self, path: str, body: dict) -> tuple[dict, dict]:
        """Returns (json body, response headers)."""
        for attempt in range(self._retries + 1):
            try:
                with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                    resp = client.post(f"{self._base}{path}", headers=self._headers, json=body)
            except httpx.TimeoutException as exc:
                if attempt == self._retries:
                    raise ProviderError("timeout", f"request to {path} timed out") from exc
                self._sleep(self._sleep_for(attempt, None))
                continue
            except httpx.HTTPError as exc:
                raise ProviderError("error", f"transport error: {type(exc).__name__}") from exc
            if resp.status_code in RETRYABLE and attempt < self._retries:
                self._sleep(self._sleep_for(attempt, resp))
                continue
            if resp.status_code >= 400:
                raise ProviderError("error", f"HTTP {resp.status_code}: {_error_message(resp)}")
            try:
                return resp.json(), dict(resp.headers)
            except ValueError as exc:
                raise ProviderError("invalid_output", "response body was not JSON", raw=resp.text[:2000]) from exc
        raise ProviderError("error", "retries exhausted")

    @contextmanager
    def stream_sse(self, path: str, body: dict) -> Iterator[Iterator[dict]]:
        """Yield an iterator of decoded SSE `data:` JSON events. Retries only before the stream opens."""
        headers = {**self._headers, "Accept": "text/event-stream"}
        for attempt in range(self._retries + 1):
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                try:
                    with client.stream("POST", f"{self._base}{path}", headers=headers, json=body) as resp:
                        if resp.status_code < 400:
                            try:
                                yield _iter_events(resp)
                            except httpx.TimeoutException as exc:
                                raise ProviderError("timeout", f"stream {path} stalled") from exc
                            except httpx.HTTPError as exc:
                                raise ProviderError("error", f"stream broke: {type(exc).__name__}") from exc
                            return
                        resp.read()
                        if resp.status_code not in RETRYABLE or attempt == self._retries:
                            raise ProviderError("error", f"HTTP {resp.status_code}: {_error_message(resp)}")
                        wait = self._sleep_for(attempt, resp)
                except httpx.TimeoutException as exc:
                    if attempt == self._retries:
                        raise ProviderError("timeout", f"stream {path} timed out") from exc
                    wait = self._sleep_for(attempt, None)
                except httpx.HTTPError as exc:
                    raise ProviderError("error", f"transport error: {type(exc).__name__}") from exc
            self._sleep(wait)
        raise ProviderError("error", "retries exhausted")


STREAM_DEADLINE_S = 300.0


def _iter_events(resp: httpx.Response, deadline_s: float = STREAM_DEADLINE_S) -> Iterator[dict]:
    """Per-read timeouts don't bound a slowly dripping stream; enforce an overall deadline too."""
    deadline = time.monotonic() + deadline_s
    for line in resp.iter_lines():
        if time.monotonic() > deadline:
            raise ProviderError("timeout", f"stream exceeded {deadline_s:.0f}s overall deadline")
        if not line or not line.startswith("data: "):
            continue
        data = line.removeprefix("data: ")
        if data == "[DONE]":
            return
        try:
            yield json.loads(data)
        except json.JSONDecodeError as exc:
            raise ProviderError("invalid_output", "malformed SSE event", raw=data[:2000]) from exc


def _error_message(resp: httpx.Response) -> str:
    try:
        err = resp.json().get("error", {})
        return str(err.get("message") or err.get("code") or resp.reason_phrase)[:300]
    except ValueError:
        return resp.reason_phrase
