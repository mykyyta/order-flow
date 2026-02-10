from apps.sales.domain.policies import resolve_line_production_status, resolve_sales_order_status
from apps.sales.domain.status import (
    PRODUCTION_STATUS_DONE,
    PRODUCTION_STATUS_IN_PROGRESS,
    PRODUCTION_STATUS_PENDING,
    STATUS_CANCELLED,
    STATUS_NEW,
    STATUS_PRODUCTION,
    STATUS_READY,
)


def test_resolve_line_production_status_for_zero_orders():
    assert (
        resolve_line_production_status(
            production_mode="manual_production",
            total_orders=0,
            finished_orders=0,
        )
        == PRODUCTION_STATUS_PENDING
    )
    assert (
        resolve_line_production_status(
            production_mode="auto",
            total_orders=0,
            finished_orders=0,
        )
        == PRODUCTION_STATUS_DONE
    )


def test_resolve_line_production_status_for_existing_orders():
    assert (
        resolve_line_production_status(
            production_mode="auto",
            total_orders=2,
            finished_orders=0,
        )
        == PRODUCTION_STATUS_PENDING
    )
    assert (
        resolve_line_production_status(
            production_mode="auto",
            total_orders=2,
            finished_orders=1,
        )
        == PRODUCTION_STATUS_IN_PROGRESS
    )
    assert (
        resolve_line_production_status(
            production_mode="auto",
            total_orders=2,
            finished_orders=2,
        )
        == PRODUCTION_STATUS_DONE
    )


def test_resolve_sales_order_status_with_lines():
    assert (
        resolve_sales_order_status(
            status=STATUS_NEW,
            line_production_statuses=[PRODUCTION_STATUS_PENDING, PRODUCTION_STATUS_DONE],
        )
        == STATUS_PRODUCTION
    )
    assert (
        resolve_sales_order_status(
            status=STATUS_PRODUCTION,
            line_production_statuses=[PRODUCTION_STATUS_DONE, PRODUCTION_STATUS_DONE],
        )
        == STATUS_READY
    )


def test_resolve_sales_order_status_is_none_for_terminal_or_unchanged():
    assert (
        resolve_sales_order_status(
            status=STATUS_CANCELLED,
            line_production_statuses=[PRODUCTION_STATUS_DONE],
        )
        is None
    )
    assert (
        resolve_sales_order_status(
            status=STATUS_PRODUCTION,
            line_production_statuses=[PRODUCTION_STATUS_PENDING],
        )
        is None
    )
    assert (
        resolve_sales_order_status(
            status=STATUS_NEW,
            line_production_statuses=[],
        )
        is None
    )
