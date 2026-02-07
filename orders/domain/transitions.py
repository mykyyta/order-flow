from __future__ import annotations

from typing import Set

from orders.domain.order_statuses import get_allowed_transitions as _get_allowed_transitions


def is_transition_allowed(current_status: str, next_status: str) -> bool:
    return next_status in _get_allowed_transitions(current_status)


def get_allowed_transitions(current_status: str) -> Set[str]:
    return set(_get_allowed_transitions(current_status))
