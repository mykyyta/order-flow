"""Form tests for orders."""

import pytest

from apps.production.forms import OrderForm

from .conftest import ColorFactory, ProductFactory


@pytest.mark.django_db
def test_order_form_product_and_color_have_named_placeholders_and_sorted_choices():
    ProductFactory(name="Zeta")
    ProductFactory(name="Alpha")
    ColorFactory(name="Blue", code=101)
    ColorFactory(name="Amber", code=102)

    form = OrderForm()

    product_choice_labels = [label for _, label in list(form.fields["product"].choices)]
    assert product_choice_labels[0] == "—"
    assert product_choice_labels[1:] == ["Alpha", "Zeta"]

    color_choice_labels = [label for _, label in list(form.fields["color"].choices)]
    assert color_choice_labels[0] == "—"
    assert color_choice_labels[1:] == ["Amber", "Blue"]

    product_html = str(form["product"])
    assert 'option value=""' in product_html
    assert "disabled" in product_html

    color_html = str(form["color"])
    assert 'option value=""' in color_html
    assert "disabled" in color_html
