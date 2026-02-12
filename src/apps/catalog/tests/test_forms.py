"""Form tests for catalog app."""
import pytest

from apps.catalog.forms import ColorForm, ProductForm


@pytest.mark.django_db
class TestColorForm:
    def test_clean_name_capitalizes(self):
        form = ColorForm(data={"name": "blue sky", "code": 100, "status": ""})
        assert form.is_valid()
        assert form.cleaned_data["name"] == "Blue sky"

    def test_clean_status_defaults_to_in_stock(self):
        form = ColorForm(data={"name": "Red", "code": 101, "status": ""})
        assert form.is_valid()
        assert form.cleaned_data["status"] == "in_stock"

    def test_clean_status_preserves_value(self):
        form = ColorForm(data={"name": "Green", "code": 102, "status": "low_stock"})
        assert form.is_valid()
        assert form.cleaned_data["status"] == "low_stock"


@pytest.mark.django_db
class TestProductForm:
    def test_clean_name_capitalizes(self):
        form = ProductForm(data={"name": "mini bag"})
        assert form.is_valid()
        assert form.cleaned_data["name"] == "Mini bag"
