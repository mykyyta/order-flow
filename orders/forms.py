from django import forms
from orders.domain.order_statuses import status_choices
from .models import Order
from .models import Color, ProductModel

# Design system: one class set for all form controls (see static/css/input.css)
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
            "comment": forms.Textarea(attrs={"class": FORM_TEXTAREA, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["color"].queryset = Color.objects.filter(
            availability_status__in=["in_stock", "low_stock"]
        )


class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ["name", "code", "availability_status"]
        widgets = {
            "name": forms.TextInput(attrs={"class": FORM_INPUT}),
            "code": forms.NumberInput(attrs={"class": FORM_INPUT}),
            "availability_status": forms.Select(attrs={"class": FORM_SELECT}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        return name.capitalize()


class ProductModelForm(forms.ModelForm):
    class Meta:
        model = ProductModel
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": FORM_INPUT}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        return name.capitalize()


class OrderStatusUpdateForm(forms.Form):
    orders = forms.ModelMultipleChoiceField(
        queryset=Order.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Вибрати замовлення",
    )
    new_status = forms.ChoiceField(
        choices=status_choices(include_legacy=False, include_terminal=True),
        label="Новий статус",
    )
