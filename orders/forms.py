from django import forms

from catalog.models import Color, ProductModel
from orders.domain.order_statuses import status_choices

from .models import Order

# Design system: one class set for all form controls (see assets/tailwind/input.css)
FORM_INPUT = "form-input"
FORM_SELECT = "form-select"
FORM_TEXTAREA = "form-textarea"
FORM_CHECKBOX = "form-checkbox"


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["model", "color", "etsy", "embroidery", "urgent", "comment"]
        widgets = {
            "model": forms.Select(attrs={"class": FORM_SELECT}),
            "color": forms.Select(attrs={"class": FORM_SELECT}),
            "etsy": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
            "urgent": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
            "embroidery": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
            "comment": forms.Textarea(
                attrs={
                    "class": FORM_TEXTAREA,
                    "rows": 3,
                    "placeholder": "Коментар (необов'язково)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["color"].queryset = Color.objects.filter(
            availability_status__in=["in_stock", "low_stock"]
        )


class OrderStatusUpdateForm(forms.Form):
    orders = forms.ModelMultipleChoiceField(
        queryset=Order.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Позначити замовлення",
    )
    new_status = forms.ChoiceField(
        choices=status_choices(include_legacy=False, include_terminal=True),
        label="Новий статус",
    )
