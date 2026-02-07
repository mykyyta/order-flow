from __future__ import annotations

STATUS_NEW = "new"
STATUS_EMBROIDERY = "embroidery"
STATUS_ALMOST_FINISHED = "almost_finished"
STATUS_FINISHED = "finished"
STATUS_ON_HOLD = "on_hold"

ALLOWED_STATUSES = {
    STATUS_NEW,
    STATUS_EMBROIDERY,
    STATUS_ALMOST_FINISHED,
    STATUS_FINISHED,
    STATUS_ON_HOLD,
}


def normalize_status(value: str) -> str:
    return value.strip().lower()


def validate_status(value: str) -> str:
    normalized = normalize_status(value)
    if normalized not in ALLOWED_STATUSES:
        raise ValueError(f"Unknown status: {value}")
    return normalized
