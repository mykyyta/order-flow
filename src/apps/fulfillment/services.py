from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from apps.inventory.models import WIPStockMovement
from apps.inventory.services import remove_from_wip_stock, transfer_finished_stock
from apps.materials.services import receive_purchase_order_line, transfer_material_stock
from apps.production.domain.status import STATUS_FINISHED
from apps.production.services import change_production_order_status
from apps.sales.services import (
    create_production_orders_for_sales_order as create_production_orders_for_sales_order_v2,
)
from apps.sales.services import create_sales_order

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from decimal import Decimal

    from apps.materials.models import Material, MaterialColor
    from apps.materials.models import PurchaseOrderLine
    from apps.production.models import ProductionOrder
    from apps.sales.models import SalesOrder


def create_sales_order_orchestrated(
    *,
    source: str,
    customer_info: str,
    lines_data: list[dict[str, object]],
    notes: str = "",
    create_production_orders_now: bool = False,
    created_by: "AbstractBaseUser | None" = None,
    orders_url: str | None = None,
) -> "SalesOrder":
    return create_sales_order(
        source=source,
        customer_info=customer_info,
        lines_data=lines_data,
        notes=notes,
        create_production_orders=create_production_orders_now,
        created_by=created_by,
        orders_url=orders_url,
    )


def create_production_orders_for_sales_order(
    *,
    sales_order: "SalesOrder",
    created_by: "AbstractBaseUser",
    orders_url: str | None = None,
) -> list["ProductionOrder"]:
    return create_production_orders_for_sales_order_v2(
        sales_order=sales_order,
        created_by=created_by,
        orders_url=orders_url,
    )


def receive_purchase_order_line_orchestrated(
    *,
    purchase_order_line: "PurchaseOrderLine",
    quantity: Decimal,
    warehouse_id: int | None = None,
    received_by: "AbstractBaseUser | None" = None,
    notes: str = "",
):
    return receive_purchase_order_line(
        purchase_order_line=purchase_order_line,
        quantity=quantity,
        warehouse_id=warehouse_id,
        received_by=received_by,
        notes=notes,
    )


def complete_production_order(
    *,
    production_order: "ProductionOrder",
    changed_by: "AbstractBaseUser",
) -> None:
    change_production_order_status(
        production_orders=[production_order],
        new_status=STATUS_FINISHED,
        changed_by=changed_by,
    )


def scrap_wip(
    *,
    variant_id: int,
    quantity: int,
    user: "AbstractBaseUser | None" = None,
    warehouse_id: int | None = None,
    notes: str = "",
):
    return remove_from_wip_stock(
        warehouse_id=warehouse_id,
        variant_id=variant_id,
        quantity=quantity,
        reason=WIPStockMovement.Reason.SCRAP_OUT,
        user=user,
        notes=notes,
    )


def transfer_finished_stock_orchestrated(
    *,
    from_warehouse_id: int,
    to_warehouse_id: int,
    variant_id: int,
    quantity: int,
    user: "AbstractBaseUser | None" = None,
    notes: str = "",
):
    return transfer_finished_stock(
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        variant_id=variant_id,
        quantity=quantity,
        user=user,
        notes=notes,
    )


def transfer_material_stock_orchestrated(
    *,
    from_warehouse_id: int,
    to_warehouse_id: int,
    material: "Material",
    quantity: "Decimal",
    unit: str,
    material_color: "MaterialColor | None" = None,
    user: "AbstractBaseUser | None" = None,
    notes: str = "",
):
    return transfer_material_stock(
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        material=material,
        quantity=quantity,
        unit=unit,
        material_color=material_color,
        created_by=user,
        notes=notes,
    )
