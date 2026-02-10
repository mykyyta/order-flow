from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from apps.production.models import ProductionOrder
    from apps.sales.models import SalesOrder, SalesOrderLine


def create_sales_order(
    *,
    source: str,
    customer_info: str,
    lines_data: list[dict[str, object]],
    notes: str = "",
    create_production_orders: bool = False,
    created_by: "AbstractBaseUser | None" = None,
    orders_url: str | None = None,
) -> "SalesOrder":
    from apps.customer_orders.services import create_customer_order

    return create_customer_order(
        source=source,
        customer_info=customer_info,
        lines_data=lines_data,
        notes=notes,
        create_production_orders=create_production_orders,
        created_by=created_by,
        orders_url=orders_url,
        via_v2_context=True,
    )


def create_production_orders_for_sales_order(
    *,
    sales_order: "SalesOrder",
    created_by: "AbstractBaseUser",
    orders_url: str | None = None,
) -> list["ProductionOrder"]:
    from apps.customer_orders.services import create_missing_production_orders

    return create_missing_production_orders(
        customer_order=sales_order,
        created_by=created_by,
        orders_url=orders_url,
        via_v2_context=True,
    )


def sync_sales_order_line_production(
    line: "SalesOrderLine",
    *,
    via_v2_context: bool = False,
) -> None:
    from apps.customer_orders.services import sync_customer_order_line_production

    sync_customer_order_line_production(
        line=line,
        via_v2_context=via_v2_context,
    )
