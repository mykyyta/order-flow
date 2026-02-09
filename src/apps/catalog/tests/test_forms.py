"""Form tests for catalog app."""
import pytest

from apps.catalog.forms import ColorForm, ProductModelForm


@pytest.mark.django_db
class TestColorForm:
    def test_clean_name_capitalizes(self):
        form = ColorForm(data={"name": "blue sky", "code": 100, "availability_status": ""})
        assert form.is_valid()
        assert form.cleaned_data["name"] == "Blue sky"

    def test_clean_availability_status_defaults_to_in_stock(self):
        form = ColorForm(data={"name": "Red", "code": 101, "availability_status": ""})
        assert form.is_valid()
        assert form.cleaned_data["availability_status"] == "in_stock"

    def test_clean_availability_status_preserves_value(self):
        form = ColorForm(data={"name": "Green", "code": 102, "availability_status": "low_stock"})
        assert form.is_valid()
        assert form.cleaned_data["availability_status"] == "low_stock"


@pytest.mark.django_db
class TestProductModelForm:
    def test_clean_name_capitalizes(self):
        form = ProductModelForm(data={"name": "mini bag"})
        assert form.is_valid()
        assert form.cleaned_data["name"] == "Mini bag"
