from __future__ import annotations

from typing import TYPE_CHECKING

from apps.customer_orders.services import create_customer_order

if TYPE_CHECKING:
    from apps.customer_orders.models import CustomerOrder
    from apps.orders.models import CustomUser


def create_sales_order(
    *,
    source: str,
    customer_info: str,
    lines_data: list[dict[str, object]],
    notes: str = "",
    create_production_orders: bool = False,
    created_by: "CustomUser | None" = None,
    orders_url: str | None = None,
) -> "CustomerOrder":
    return create_customer_order(
        source=source,
        customer_info=customer_info,
        lines_data=lines_data,
        notes=notes,
        create_production_orders=create_production_orders,
        created_by=created_by,
        orders_url=orders_url,
    )
