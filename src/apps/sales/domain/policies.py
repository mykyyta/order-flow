from __future__ import annotations

from collections.abc import Iterable

from apps.sales.domain.status import (
    PRODUCTION_MODE_MANUAL,
    PRODUCTION_STATUS_DONE,
    PRODUCTION_STATUS_IN_PROGRESS,
    PRODUCTION_STATUS_PENDING,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_PRODUCTION,
    STATUS_READY,
    STATUS_SHIPPED,
)

TERMINAL_SALES_ORDER_STATUSES = {
    STATUS_SHIPPED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
}


def resolve_line_production_status(
    *,
    production_mode: str,
    total_orders: int,
    finished_orders: int,
) -> str:
    if total_orders == 0:
        if production_mode == PRODUCTION_MODE_MANUAL:
            return PRODUCTION_STATUS_PENDING
        return PRODUCTION_STATUS_DONE

    if finished_orders == 0:
        return PRODUCTION_STATUS_PENDING
    if finished_orders < total_orders:
        return PRODUCTION_STATUS_IN_PROGRESS
    return PRODUCTION_STATUS_DONE


def resolve_sales_order_status(
    *,
    current_status: str,
    line_production_statuses: Iterable[str],
) -> str | None:
    if current_status in TERMINAL_SALES_ORDER_STATUSES:
        return None

    statuses = list(line_production_statuses)
    if not statuses:
        return None

    if all(status == PRODUCTION_STATUS_DONE for status in statuses):
        next_status = STATUS_READY
    else:
        next_status = STATUS_PRODUCTION

    if next_status == current_status:
        return None
    return next_status
