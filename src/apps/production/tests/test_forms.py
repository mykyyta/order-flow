"""Form tests for orders."""

import pytest

from apps.production.forms import OrderForm

from .conftest import ColorFactory, ProductFactory


@pytest.mark.django_db
def test_order_form_product_and_primary_color_have_named_placeholders_and_sorted_choices():
    material_color_1 = ColorFactory(name="Banana", code=101)
    material = material_color_1.material
    ColorFactory(material=material, name="apple", code=102)
    ProductFactory(name="Zeta", primary_material=material)
    alpha = ProductFactory(name="Alpha", primary_material=material)

    form = OrderForm(data={"product": alpha.id})

    product_choice_labels = [label for _, label in list(form.fields["product"].choices)]
    assert product_choice_labels[0] == "—"
    assert product_choice_labels[1:] == ["Alpha", "Zeta"]

    color_choice_labels = [label for _, label in list(form.fields["primary_material_color"].choices)]
    assert color_choice_labels[0] == "—"
    assert color_choice_labels[1:] == [
        "apple",
        "Banana",
    ]

    product_html = str(form["product"])
    assert 'option value=""' in product_html
    assert "disabled" in product_html

    color_html = str(form["primary_material_color"])
    assert 'option value=""' in color_html
    # Color selects must allow clearing (used by "Очистити всі кольори" action in UI).
    assert "disabled" not in color_html
