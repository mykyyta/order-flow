from __future__ import annotations

from decimal import Decimal
from typing import Any
from typing import Literal

from django.db import transaction

from apps.orders.legacy_import_mappings import (
    LEGACY_FINISHED_MOVEMENT_REASON_TO_V2,
    LEGACY_MATERIAL_MOVEMENT_REASON_TO_V2,
    LEGACY_ORDER_STATUS_TO_V2,
)

ImportMode = Literal["dry-run", "apply", "verify"]

def run_import_legacy(*, mode: ImportMode, strict: bool = False) -> dict[str, object]:
    if mode == "dry-run":
        if strict:
            raise ValueError("Strict mode is supported only for verify mode.")
        return _run_dry_run()
    if mode == "apply":
        if strict:
            raise ValueError("Strict mode is supported only for verify mode.")
        return _run_apply()
    if mode == "verify":
        return _run_verify(strict=strict)

    raise ValueError(f"Unsupported import mode: {mode}")


def run_final_import_and_verify() -> dict[str, object]:
    apply_result = _run_apply()
    verify_result = _run_verify(strict=True)
    result = "ok" if verify_result["result"] == "ok" else "failed"
    return {
        "mode": "final",
        "result": result,
        "apply": apply_result,
        "verify": verify_result,
    }


def _run_dry_run() -> dict[str, object]:
    pending_updates = _collect_pending_mapping_updates()
    unknown_values = _collect_unknown_mapped_values()
    aggregates = _collect_aggregate_snapshot()
    checks = _build_verify_checks(
        aggregates=aggregates,
        unknown_values=unknown_values,
    )
    return {
        "mode": "dry-run",
        "result": "ok",
        "pending_updates": pending_updates,
        "unknown_values": unknown_values,
        "checks": checks,
        "aggregates": aggregates,
        "note": "Dry-run calculated pending updates and verify checks without writes.",
    }


@transaction.atomic
def _run_apply() -> dict[str, object]:
    updated = _apply_status_and_reason_mappings()
    pending_updates = _collect_pending_mapping_updates()
    return {
        "mode": "apply",
        "result": "ok",
        "updated": updated,
        "pending_updates": pending_updates,
        "note": "Apply mode executed status/reason normalization via legacy mappings.",
    }


def _run_verify(*, strict: bool) -> dict[str, object]:
    mappings = {
        "order_statuses": len(LEGACY_ORDER_STATUS_TO_V2),
        "finished_movement_reasons": len(LEGACY_FINISHED_MOVEMENT_REASON_TO_V2),
        "material_movement_reasons": len(LEGACY_MATERIAL_MOVEMENT_REASON_TO_V2),
    }
    unknown_values = _collect_unknown_mapped_values()
    aggregates = _collect_aggregate_snapshot()
    checks = _build_verify_checks(
        aggregates=aggregates,
        unknown_values=unknown_values,
    )
    result_status = "failed" if strict and not checks["passed"] else "ok"
    return {
        "mode": "verify",
        "result": result_status,
        "checks": checks,
        "unknown_values": unknown_values,
        "aggregates": aggregates,
        "mappings": mappings,
        "note": "Verify mode scaffold is ready for aggregate checks.",
    }


def _collect_aggregate_snapshot() -> dict[str, object]:
    from apps.catalog.models import ProductVariant
    from apps.customer_orders.models import CustomerOrder, CustomerOrderLine
    from apps.inventory.models import StockMovement, StockRecord
    from apps.material_inventory.models import MaterialStockMovement, MaterialStockRecord
    from apps.orders.models import Order
    from django.db.models import Sum

    finished_stock_total = StockRecord.objects.aggregate(total=Sum("quantity"))["total"] or 0
    finished_movement_net = StockMovement.objects.aggregate(total=Sum("quantity_change"))["total"] or 0
    material_stock_total = (
        MaterialStockRecord.objects.aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    )
    material_movement_net = (
        MaterialStockMovement.objects.aggregate(total=Sum("quantity_change"))["total"] or Decimal("0")
    )

    return {
        "orders": Order.objects.count(),
        "sales_orders": CustomerOrder.objects.count(),
        "sales_order_lines": CustomerOrderLine.objects.count(),
        "product_variants": ProductVariant.objects.count(),
        "finished_stock_records": StockRecord.objects.count(),
        "material_stock_records": MaterialStockRecord.objects.count(),
        "finished_stock_quantity_total": int(finished_stock_total),
        "finished_movement_net_total": int(finished_movement_net),
        "finished_balance_delta": int(finished_stock_total - finished_movement_net),
        "material_stock_quantity_total": _decimal_to_str(material_stock_total),
        "material_movement_net_total": _decimal_to_str(material_movement_net),
        "material_balance_delta": _decimal_to_str(material_stock_total - material_movement_net),
        "finished_balances_by_warehouse": _collect_finished_balances_by_warehouse(),
        "material_balances_by_warehouse_unit": _collect_material_balances_by_warehouse_unit(),
    }


def _collect_finished_balances_by_warehouse() -> list[dict[str, object]]:
    from apps.inventory.models import StockMovement, StockRecord
    from django.db.models import Sum

    stock_by_warehouse: dict[str, int] = {}
    for row in (
        StockRecord.objects.values("warehouse__code")
        .annotate(stock_total=Sum("quantity"))
        .order_by("warehouse__code")
    ):
        warehouse_code = row["warehouse__code"] or "UNASSIGNED"
        stock_by_warehouse[warehouse_code] = int(row["stock_total"] or 0)

    movement_by_warehouse: dict[str, int] = {}
    for row in (
        StockMovement.objects.values("stock_record__warehouse__code")
        .annotate(movement_total=Sum("quantity_change"))
        .order_by("stock_record__warehouse__code")
    ):
        warehouse_code = row["stock_record__warehouse__code"] or "UNASSIGNED"
        movement_by_warehouse[warehouse_code] = int(row["movement_total"] or 0)

    all_codes = sorted(set(stock_by_warehouse) | set(movement_by_warehouse))
    return [
        {
            "warehouse_code": code,
            "stock_total": stock_by_warehouse.get(code, 0),
            "movement_net_total": movement_by_warehouse.get(code, 0),
            "delta": stock_by_warehouse.get(code, 0) - movement_by_warehouse.get(code, 0),
        }
        for code in all_codes
    ]


def _collect_material_balances_by_warehouse_unit() -> list[dict[str, str]]:
    from apps.material_inventory.models import MaterialStockMovement, MaterialStockRecord
    from django.db.models import Sum

    stock_by_key: dict[tuple[str, str], Decimal] = {}
    for row in (
        MaterialStockRecord.objects.values("warehouse__code", "unit")
        .annotate(stock_total=Sum("quantity"))
        .order_by("warehouse__code", "unit")
    ):
        warehouse_code = row["warehouse__code"] or "UNASSIGNED"
        unit = str(row["unit"])
        stock_by_key[(warehouse_code, unit)] = Decimal(str(row["stock_total"] or "0"))

    movement_by_key: dict[tuple[str, str], Decimal] = {}
    for row in (
        MaterialStockMovement.objects.values("stock_record__warehouse__code", "stock_record__unit")
        .annotate(movement_total=Sum("quantity_change"))
        .order_by("stock_record__warehouse__code", "stock_record__unit")
    ):
        warehouse_code = row["stock_record__warehouse__code"] or "UNASSIGNED"
        unit = str(row["stock_record__unit"])
        movement_by_key[(warehouse_code, unit)] = Decimal(str(row["movement_total"] or "0"))

    all_keys = sorted(set(stock_by_key) | set(movement_by_key))
    return [
        {
            "warehouse_code": warehouse_code,
            "unit": unit,
            "stock_total": _decimal_to_str(stock_by_key.get((warehouse_code, unit), Decimal("0"))),
            "movement_net_total": _decimal_to_str(
                movement_by_key.get((warehouse_code, unit), Decimal("0"))
            ),
            "delta": _decimal_to_str(
                stock_by_key.get((warehouse_code, unit), Decimal("0"))
                - movement_by_key.get((warehouse_code, unit), Decimal("0"))
            ),
        }
        for warehouse_code, unit in all_keys
    ]


def _decimal_to_str(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.001")))


def _build_verify_checks(
    *,
    aggregates: dict[str, object],
    unknown_values: dict[str, list[str]],
) -> dict[str, object]:
    issues: list[dict[str, object]] = []

    finished_delta = int(aggregates["finished_balance_delta"])
    if finished_delta != 0:
        issues.append(
            {
                "code": "finished_balance_delta",
                "message": "Finished stock total does not match movement net total.",
                "delta": finished_delta,
            }
        )

    material_delta = Decimal(str(aggregates["material_balance_delta"]))
    if material_delta != Decimal("0.000"):
        issues.append(
            {
                "code": "material_balance_delta",
                "message": "Material stock total does not match movement net total.",
                "delta": _decimal_to_str(material_delta),
            }
        )

    for row in aggregates["finished_balances_by_warehouse"]:
        delta = int(row["delta"])
        if delta != 0:
            issues.append(
                {
                    "code": "finished_balance_by_warehouse",
                    "message": "Finished warehouse balance delta is non-zero.",
                    "warehouse_code": row["warehouse_code"],
                    "delta": delta,
                }
            )

    for row in aggregates["material_balances_by_warehouse_unit"]:
        delta = Decimal(str(row["delta"]))
        if delta != Decimal("0.000"):
            issues.append(
                {
                    "code": "material_balance_by_warehouse_unit",
                    "message": "Material balance delta is non-zero for warehouse/unit.",
                    "warehouse_code": row["warehouse_code"],
                    "unit": row["unit"],
                    "delta": _decimal_to_str(delta),
                }
            )

    for key, values in unknown_values.items():
        if values:
            issues.append(
                {
                    "code": f"unknown_{key}",
                    "message": "Found unmapped legacy values.",
                    "values": values,
                }
            )

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


def _apply_status_and_reason_mappings() -> dict[str, int]:
    from apps.inventory.models import StockMovement
    from apps.material_inventory.models import MaterialStockMovement
    from apps.orders.models import Order, OrderStatusHistory

    return {
        "order_statuses": _apply_mapping_updates(
            model=Order,
            field="current_status",
            mapping=LEGACY_ORDER_STATUS_TO_V2,
        ),
        "order_status_history": _apply_mapping_updates(
            model=OrderStatusHistory,
            field="new_status",
            mapping=LEGACY_ORDER_STATUS_TO_V2,
        ),
        "finished_movement_reasons": _apply_mapping_updates(
            model=StockMovement,
            field="reason",
            mapping=LEGACY_FINISHED_MOVEMENT_REASON_TO_V2,
        ),
        "material_movement_reasons": _apply_mapping_updates(
            model=MaterialStockMovement,
            field="reason",
            mapping=LEGACY_MATERIAL_MOVEMENT_REASON_TO_V2,
        ),
    }


def _apply_mapping_updates(
    *,
    model: type[Any],
    field: str,
    mapping: dict[str, str],
) -> int:
    updated_count = 0
    for legacy_value, mapped_value in mapping.items():
        if legacy_value == mapped_value:
            continue
        updated_count += model.objects.filter(**{field: legacy_value}).update(**{field: mapped_value})
    return updated_count


def _collect_pending_mapping_updates() -> dict[str, int]:
    from apps.inventory.models import StockMovement
    from apps.material_inventory.models import MaterialStockMovement
    from apps.orders.models import Order, OrderStatusHistory

    return {
        "order_statuses": _count_pending_mapping_updates(
            model=Order,
            field="current_status",
            mapping=LEGACY_ORDER_STATUS_TO_V2,
        ),
        "order_status_history": _count_pending_mapping_updates(
            model=OrderStatusHistory,
            field="new_status",
            mapping=LEGACY_ORDER_STATUS_TO_V2,
        ),
        "finished_movement_reasons": _count_pending_mapping_updates(
            model=StockMovement,
            field="reason",
            mapping=LEGACY_FINISHED_MOVEMENT_REASON_TO_V2,
        ),
        "material_movement_reasons": _count_pending_mapping_updates(
            model=MaterialStockMovement,
            field="reason",
            mapping=LEGACY_MATERIAL_MOVEMENT_REASON_TO_V2,
        ),
    }


def _count_pending_mapping_updates(
    *,
    model: type[Any],
    field: str,
    mapping: dict[str, str],
) -> int:
    pending = 0
    for legacy_value, mapped_value in mapping.items():
        if legacy_value == mapped_value:
            continue
        pending += model.objects.filter(**{field: legacy_value}).count()
    return pending


def _collect_unknown_mapped_values() -> dict[str, list[str]]:
    from apps.inventory.models import StockMovement
    from apps.material_inventory.models import MaterialStockMovement
    from apps.orders.models import Order, OrderStatusHistory

    return {
        "order_statuses": _collect_unknown_field_values(
            model=Order,
            field="current_status",
            known_values=set(LEGACY_ORDER_STATUS_TO_V2),
        ),
        "order_status_history": _collect_unknown_field_values(
            model=OrderStatusHistory,
            field="new_status",
            known_values=set(LEGACY_ORDER_STATUS_TO_V2),
        ),
        "finished_movement_reasons": _collect_unknown_field_values(
            model=StockMovement,
            field="reason",
            known_values=set(LEGACY_FINISHED_MOVEMENT_REASON_TO_V2),
        ),
        "material_movement_reasons": _collect_unknown_field_values(
            model=MaterialStockMovement,
            field="reason",
            known_values=set(LEGACY_MATERIAL_MOVEMENT_REASON_TO_V2),
        ),
    }


def _collect_unknown_field_values(
    *,
    model: type[Any],
    field: str,
    known_values: set[str],
) -> list[str]:
    values = {
        value
        for value in model.objects.values_list(field, flat=True).distinct()
        if value is not None
    }
    return sorted(value for value in values if value not in known_values)
