from unittest.mock import sentinel
from unittest.mock import patch

import pytest

from apps.materials.procurement_services import (
    LegacyWritesFrozenError,
    add_material_stock as legacy_add_material_stock,
    receive_purchase_order_line as legacy_receive_purchase_order_line,
    remove_material_stock as legacy_remove_material_stock,
)


def test_legacy_procurement_services_delegate_to_new_context_services():
    with (
        patch("apps.materials.procurement_services._add_material_stock", return_value=sentinel.add_result),
        patch(
            "apps.materials.procurement_services._remove_material_stock",
            return_value=sentinel.remove_result,
        ),
        patch(
            "apps.materials.procurement_services._receive_purchase_order_line",
            return_value=sentinel.receive_result,
        ),
    ):
        assert legacy_add_material_stock(material=object(), quantity=1, unit="m", reason="r") is sentinel.add_result
        assert (
            legacy_remove_material_stock(material=object(), quantity=1, unit="m", reason="r")
            is sentinel.remove_result
        )
        assert (
            legacy_receive_purchase_order_line(purchase_order_line=object(), quantity=1)
            is sentinel.receive_result
        )


@pytest.mark.parametrize(
    "func,kwargs",
    [
        (legacy_add_material_stock, {"material": object(), "quantity": 1, "unit": "m", "reason": "r"}),
        (legacy_remove_material_stock, {"material": object(), "quantity": 1, "unit": "m", "reason": "r"}),
        (legacy_receive_purchase_order_line, {"purchase_order_line": object(), "quantity": 1}),
    ],
)
def test_legacy_procurement_services_block_writes_when_freeze_enabled(settings, func, kwargs):
    settings.FREEZE_LEGACY_WRITES = True

    with pytest.raises(LegacyWritesFrozenError, match="frozen"):
        func(**kwargs)
