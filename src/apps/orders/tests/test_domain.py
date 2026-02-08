"""Domain and model status tests."""
import pytest

from apps.orders.domain.status import STATUS_FINISHED, STATUS_NEW

from .conftest import ColorFactory, OrderFactory, ProductModelFactory


@pytest.mark.django_db
def test_get_status_uses_current_status():
    model = ProductModelFactory()
    color = ColorFactory()
    order = OrderFactory(model=model, color=color, current_status=STATUS_NEW)
    from apps.orders.models import OrderStatusHistory
    OrderStatusHistory.objects.create(order=order, changed_by=None, new_status=STATUS_FINISHED)
    assert order.get_status() == STATUS_NEW
