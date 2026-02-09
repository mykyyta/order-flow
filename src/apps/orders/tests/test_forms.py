"""Form tests for orders."""

import pytest

from apps.orders.forms import OrderForm

from .conftest import ColorFactory, ProductModelFactory


@pytest.mark.django_db
def test_order_form_model_and_color_have_named_placeholders_and_sorted_choices():
    ProductModelFactory(name="Zeta")
    ProductModelFactory(name="Alpha")
    ColorFactory(name="Blue", code=101)
    ColorFactory(name="Amber", code=102)

    form = OrderForm()

    model_choice_labels = [label for _, label in list(form.fields["model"].choices)]
    assert model_choice_labels[0] == "—"
    assert model_choice_labels[1:] == ["Alpha", "Zeta"]

    color_choice_labels = [label for _, label in list(form.fields["color"].choices)]
    assert color_choice_labels[0] == "—"
    assert color_choice_labels[1:] == ["Amber", "Blue"]

    model_html = str(form["model"])
    assert 'option value=""' in model_html
    assert "disabled" in model_html

    color_html = str(form["color"])
    assert 'option value=""' in color_html
    assert "disabled" in color_html
