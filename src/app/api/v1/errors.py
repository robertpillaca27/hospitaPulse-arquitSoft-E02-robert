"""HTTP error response conventions for version 1."""

from __future__ import annotations

from typing import TypedDict


class ApiError(TypedDict):
    """Stable public shape for translated application errors."""

    code: str
    message: str
    details: dict[str, str] | None
    request_id: str | None
