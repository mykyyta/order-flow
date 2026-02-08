from django.test import SimpleTestCase

from catalog.models import Color, ProductModel


class CatalogModelsTests(SimpleTestCase):
    """Smoke tests for catalog models (no DB)."""

    def test_product_model_str(self):
        pm = ProductModel(name="Test")
        self.assertIn("Test", str(pm))

    def test_color_str(self):
        c = Color(name="Red", code=1)
        self.assertIn("Red", str(c))
