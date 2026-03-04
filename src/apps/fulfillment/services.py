from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Sum

from apps.inventory.models import WIPStockMovement
from apps.inventory.models import ProductStockMovement, ProductStockReservation
from apps.inventory.services import (
    remove_from_stock,
    remove_from_wip_stock,
    reserve_stock_up_to,
    transfer_finished_stock,
)
from apps.materials.services import (
    calculate_material_requirements_for_variant,
    get_material_stock_quantity,
)
from apps.materials.services import receive_purchase_order_line, transfer_material_stock
from apps.production.domain.status import STATUS_DONE
from apps.production.services import change_production_order_status, create_production_order
from apps.sales.models import SalesOrderLine, SalesOrderLineBlocker
from apps.sales.services import (
    create_production_orders_for_sales_order as create_production_orders_for_sales_order_v2,
)
from apps.sales.services import create_sales_order, get_sales_order_line_variant_requirements
from apps.sales.services import sync_sales_order_line_production
from apps.warehouses.services import get_default_warehouse

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
    warehouse_id: int,
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
        new_status=STATUS_DONE,
        changed_by=changed_by,
        on_sales_line_done=sync_sales_order_line_production,
    )
    if production_order.sales_order_line_id:
        plan_sales_order(
            sales_order=production_order.sales_order_line.sales_order,
            planned_by=changed_by,
        )


def scrap_wip(
    *,
    variant_id: int,
    quantity: int,
    warehouse_id: int,
    user: "AbstractBaseUser | None" = None,
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


@transaction.atomic
def plan_sales_order(
    *,
    sales_order: "SalesOrder",
    planned_by: "AbstractBaseUser",
    orders_url: str | None = None,
) -> dict[str, int]:
    from apps.catalog.models import Variant
    from apps.sales.models import SalesOrder

    order = SalesOrder.objects.select_for_update().get(pk=sales_order.pk)
    if order.status in {SalesOrder.Status.SHIPPED, SalesOrder.Status.COMPLETED, SalesOrder.Status.CANCELLED}:
        raise ValueError("Не можна планувати замовлення в кінцевому статусі.")

    warehouse = get_default_warehouse()
    lines = list(
        SalesOrderLine.objects.select_for_update()
        .filter(sales_order_id=order.id)
        .select_related("product", "variant")
    )
    line_ids = [line.id for line in lines]

    # Planning is idempotent: reset active blockers/reservations and compute from scratch.
    SalesOrderLineBlocker.objects.filter(sales_order_line_id__in=line_ids, is_active=True).update(
        is_active=False
    )
    ProductStockReservation.objects.filter(
        sales_order_line_id__in=line_ids,
        status=ProductStockReservation.Status.ACTIVE,
    ).update(status=ProductStockReservation.Status.RELEASED)

    created_production_orders = 0
    variants_by_id: dict[int, Variant] = {}

    for line in lines:
        requirements = get_sales_order_line_variant_requirements(line=line)
        if not requirements:
            continue

        for variant_id, required_qty in requirements:
            if line.production_mode == line.ProductionMode.FORCE:
                reserved_qty = 0
                deficit_qty = required_qty
            else:
                reserved_qty = reserve_stock_up_to(
                    warehouse_id=warehouse.id,
                    sales_order_line_id=line.id,
                    variant_id=variant_id,
                    quantity=required_qty,
                    notes=f"Sales order #{order.id}, line #{line.id}",
                )
                deficit_qty = required_qty - reserved_qty

            if deficit_qty <= 0:
                continue

            open_production_qty = line.production_orders.filter(variant_id=variant_id).exclude(
                status=STATUS_DONE
            ).count()
            to_create_qty = max(deficit_qty - open_production_qty, 0)
            if to_create_qty <= 0:
                continue

            if line.production_mode == line.ProductionMode.MANUAL:
                SalesOrderLineBlocker.objects.update_or_create(
                    sales_order_line=line,
                    code=SalesOrderLineBlocker.Code.MANUAL_REQUIRED,
                    defaults={
                        "is_active": True,
                        "details": {
                            "variant_id": variant_id,
                            "required_qty": required_qty,
                            "reserved_qty": reserved_qty,
                            "deficit_qty": deficit_qty,
                            "open_production_qty": open_production_qty,
                            "to_create_qty": to_create_qty,
                        },
                    },
                )
                continue

            variant = variants_by_id.get(variant_id)
            if variant is None:
                variant = Variant.objects.select_related("product").get(id=variant_id)
                variants_by_id[variant_id] = variant

            missing = _missing_materials_for_variant(
                warehouse_id=warehouse.id,
                variant=variant,
                quantity=to_create_qty,
            )
            if missing:
                SalesOrderLineBlocker.objects.update_or_create(
                    sales_order_line=line,
                    code=SalesOrderLineBlocker.Code.MISSING_MATERIALS,
                    defaults={
                        "is_active": True,
                        "details": {
                            "variant_id": variant_id,
                            "deficit_qty": deficit_qty,
                            "open_production_qty": open_production_qty,
                            "to_create_qty": to_create_qty,
                            "missing": missing,
                        },
                    },
                )
                continue

            for _ in range(to_create_qty):
                create_production_order(
                    product=variant.product,
                    variant=variant,
                    is_embroidery=False,
                    is_urgent=False,
                    is_etsy=False,
                    comment=f"Sales order #{order.id}, line #{line.id}",
                    created_by=planned_by,
                    orders_url=orders_url,
                    sales_order_line=line,
                )
                created_production_orders += 1

        sync_sales_order_line_production(line)

    _sync_sales_order_status_from_reservations(order=order, warehouse_id=warehouse.id)
    return {"created_production_orders": created_production_orders}


def _missing_materials_for_variant(*, warehouse_id: int, variant, quantity: int) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for req in calculate_material_requirements_for_variant(variant=variant, quantity=quantity):
        available = get_material_stock_quantity(
            warehouse_id=warehouse_id,
            material_id=req.material_id,
            material_color_id=req.material_color_id,
            unit=req.unit,
        )
        if available < req.quantity:
            missing.append(
                {
                    "material_id": str(req.material_id),
                    "material_color_id": str(req.material_color_id) if req.material_color_id else "",
                    "unit": req.unit,
                    "available": str(available),
                    "required": str(req.quantity),
                }
            )
    return missing


def _is_sales_order_fully_reserved(*, order, warehouse_id: int) -> bool:
    line_ids = list(order.lines.values_list("id", flat=True))
    if not line_ids:
        return False

    reserved_by_key = {
        (row["sales_order_line_id"], row["variant_id"]): int(row["total_qty"])
        for row in ProductStockReservation.objects.filter(
            sales_order_line_id__in=line_ids,
            status=ProductStockReservation.Status.ACTIVE,
            warehouse_id=warehouse_id,
        )
        .values("sales_order_line_id", "variant_id")
        .annotate(total_qty=Sum("quantity"))
    }

    for line in order.lines.select_related("product", "variant"):
        for variant_id, required_qty in get_sales_order_line_variant_requirements(line=line):
            if reserved_by_key.get((line.id, variant_id), 0) != required_qty:
                return False
    return True


def _sync_sales_order_status_from_reservations(*, order, warehouse_id: int) -> None:
    from apps.sales.models import SalesOrder

    if order.status in {SalesOrder.Status.SHIPPED, SalesOrder.Status.COMPLETED, SalesOrder.Status.CANCELLED}:
        return

    has_blockers = SalesOrderLineBlocker.objects.filter(
        sales_order_line__sales_order_id=order.id,
        is_active=True,
    ).exists()
    if has_blockers:
        new_status = SalesOrder.Status.PROCESSING
    else:
        new_status = SalesOrder.Status.READY if _is_sales_order_fully_reserved(order=order, warehouse_id=warehouse_id) else SalesOrder.Status.PRODUCTION

    if order.status != new_status:
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])


@transaction.atomic
def ship_sales_order(
    *,
    sales_order: "SalesOrder",
    shipped_by: "AbstractBaseUser",
) -> None:
    from apps.sales.models import SalesOrder

    order = SalesOrder.objects.select_for_update().get(pk=sales_order.pk)
    warehouse = get_default_warehouse()

    if order.status != SalesOrder.Status.READY:
        raise ValueError("Замовлення має бути в статусі 'Готове до відправки'.")
    if not _is_sales_order_fully_reserved(order=order, warehouse_id=warehouse.id):
        raise ValueError("Недостатньо заброньовано для відправки.")

    lines_by_id = {
        line.id: line
        for line in SalesOrderLine.objects.filter(sales_order_id=order.id).select_related("sales_order")
    }
    reservations = list(
        ProductStockReservation.objects.select_for_update()
        .filter(
            sales_order_line__sales_order_id=order.id,
            warehouse_id=warehouse.id,
            status=ProductStockReservation.Status.ACTIVE,
        )
        .select_related("variant")
    )
    for res in reservations:
        line = lines_by_id[res.sales_order_line_id]
        remove_from_stock(
            warehouse_id=warehouse.id,
            variant_id=res.variant_id,
            quantity=res.quantity,
            reason=ProductStockMovement.Reason.ORDER_OUT,
            sales_order_line=line,
            user=shipped_by,
            notes=f"Sales order #{order.id}",
        )
        res.status = ProductStockReservation.Status.CONSUMED
        res.save(update_fields=["status", "updated_at"])

    order.status = SalesOrder.Status.SHIPPED
    order.save(update_fields=["status", "updated_at"])


@transaction.atomic
def complete_sales_order(*, sales_order: "SalesOrder") -> None:
    from apps.sales.models import SalesOrder

    order = SalesOrder.objects.select_for_update().get(pk=sales_order.pk)
    if order.status != SalesOrder.Status.SHIPPED:
        raise ValueError("Замовлення має бути в статусі 'Відправлено'.")
    order.status = SalesOrder.Status.COMPLETED
    order.save(update_fields=["status", "updated_at"])


@transaction.atomic
def create_make_to_stock_production_orders(
    *,
    variant_id: int,
    quantity: int,
    created_by: "AbstractBaseUser",
    orders_url: str | None = None,
) -> list["ProductionOrder"]:
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0")

    from apps.catalog.models import Variant

    warehouse = get_default_warehouse()
    variant = Variant.objects.select_related("product").get(id=variant_id)
    missing = _missing_materials_for_variant(
        warehouse_id=warehouse.id,
        variant=variant,
        quantity=quantity,
    )
    if missing:
        raise ValueError("Недостатньо матеріалів для виробництва на склад.")

    created: list["ProductionOrder"] = []
    for _ in range(quantity):
        created.append(
            create_production_order(
                product=variant.product,
                variant=variant,
                is_embroidery=False,
                is_urgent=False,
                is_etsy=False,
                comment="Make-to-stock",
                created_by=created_by,
                orders_url=orders_url,
                sales_order_line=None,
            )
        )
    return created
