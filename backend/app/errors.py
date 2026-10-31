"""Typed API error carried to the uniform error envelope."""

from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: list | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []


class ProviderError(Exception):
    """Provider failure. `kind` is one of error | timeout | invalid_output | no_fixture | not_approved."""

    def __init__(self, kind: str, message: str, raw: str | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.raw = raw
