from __future__ import annotations

from datetime import datetime
from typing import Optional

from apps.orders.domain.status import STATUS_FINISHED


def compute_finished_at(
    *,
    current_finished_at: Optional[datetime],
    new_status: str,
    now: datetime,
) -> Optional[datetime]:
    if new_status == STATUS_FINISHED:
        return current_finished_at or now
    return None
