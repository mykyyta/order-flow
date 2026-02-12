from __future__ import annotations

from typing import Set

from apps.production.domain.order_statuses import get_allowed_transitions as _get_allowed_transitions


def is_transition_allowed(status: str, next_status: str) -> bool:
    return next_status in _get_allowed_transitions(status)


def get_allowed_transitions(status: str) -> Set[str]:
    return set(_get_allowed_transitions(status))
