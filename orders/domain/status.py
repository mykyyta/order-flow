from __future__ import annotations

from orders.domain.order_statuses import (  # noqa: F401
    ACTIVE_STATUS_CODES,
    STATUS_ALMOST_FINISHED,
    STATUS_DECIDING,
    STATUS_DOING,
    STATUS_EMBROIDERY,
    STATUS_FINISHED,
    STATUS_NEW,
    STATUS_ON_HOLD,
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
