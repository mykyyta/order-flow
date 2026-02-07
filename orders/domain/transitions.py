from __future__ import annotations

from typing import Dict, Set

from orders.domain.status import (
    STATUS_ALMOST_FINISHED,
    STATUS_EMBROIDERY,
    STATUS_FINISHED,
    STATUS_NEW,
    STATUS_ON_HOLD,
)

_ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    STATUS_NEW: {
        STATUS_EMBROIDERY,
        STATUS_ALMOST_FINISHED,
        STATUS_FINISHED,
        STATUS_ON_HOLD,
    },
    STATUS_EMBROIDERY: {
        STATUS_ALMOST_FINISHED,
        STATUS_FINISHED,
        STATUS_ON_HOLD,
    },
    STATUS_ALMOST_FINISHED: {
        STATUS_FINISHED,
        STATUS_ON_HOLD,
    },
    STATUS_ON_HOLD: {
        STATUS_NEW,
        STATUS_EMBROIDERY,
        STATUS_ALMOST_FINISHED,
        STATUS_FINISHED,
    },
    STATUS_FINISHED: set(),
}


def is_transition_allowed(current_status: str, next_status: str) -> bool:
    allowed = _ALLOWED_TRANSITIONS.get(current_status)
    if allowed is None:
        return False
    return next_status in allowed
