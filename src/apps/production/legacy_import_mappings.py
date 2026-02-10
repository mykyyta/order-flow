from __future__ import annotations

LEGACY_ORDER_STATUS_TO_V2 = {
    "new": "new",
    "doing": "doing",
    "is_embroidery": "is_embroidery",
    "deciding": "deciding",
    "on_hold": "on_hold",
    "finished": "finished",
    # Legacy-only status is normalized to terminal finished state in V2.
    "almost_finished": "finished",
}

LEGACY_FINISHED_MOVEMENT_REASON_TO_V2 = {
    "production_in": "production_in",
    "order_out": "order_out",
    "adjustment_in": "adjustment_in",
    "adjustment_out": "adjustment_out",
    "return_in": "return_in",
    # Transfer reasons are preserved in V2 for multi-warehouse flows.
    "transfer_in": "transfer_in",
    "transfer_out": "transfer_out",
}

LEGACY_MATERIAL_MOVEMENT_REASON_TO_V2 = {
    "purchase_in": "purchase_in",
    "production_out": "production_out",
    "adjustment_in": "adjustment_in",
    "adjustment_out": "adjustment_out",
    "return_in": "return_in",
    "transfer_in": "transfer_in",
    "transfer_out": "transfer_out",
}
