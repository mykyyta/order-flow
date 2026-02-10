from __future__ import annotations

from apps.production.domain.order_statuses import (  # noqa: F401
    ACTIVE_STATUS_CODES,
    STATUS_BLOCKED,
    STATUS_DECIDING,
    STATUS_DONE,
    STATUS_EMBROIDERY,
    STATUS_IN_PROGRESS,
    STATUS_NEW,
)

ALLOWED_STATUSES = {
    *ACTIVE_STATUS_CODES,
}


def normalize_status(value: str) -> str:
    return value.strip().lower()


def validate_status(value: str) -> str:
    normalized = normalize_status(value)
    if normalized not in ALLOWED_STATUSES:
        raise ValueError(f"Unknown status: {value}")
    return normalized
