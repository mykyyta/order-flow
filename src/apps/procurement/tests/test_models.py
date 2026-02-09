import pytest

from apps.materials.models import SupplierMaterialOffer
from apps.procurement.models import SupplierOffer


@pytest.mark.django_db
def test_supplier_offer_alias_points_to_legacy_model():
    assert SupplierOffer is SupplierMaterialOffer
