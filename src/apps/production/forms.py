from django import forms

from apps.catalog.models import Color, Product
from apps.catalog.variants import resolve_or_create_product_variant
from apps.production.domain.order_statuses import status_choices
from apps.production.models import ProductionOrder

# Design system: one class set for all form controls (see assets/tailwind/input.css)
FORM_INPUT = "form-input"
FORM_SELECT = "form-select"
FORM_TEXTAREA = "form-textarea"
FORM_CHECKBOX = "form-checkbox"


class HiddenEmptyOptionSelect(forms.Select):
    def create_option(self, *args, **kwargs):
        option = super().create_option(*args, **kwargs)
        if option["value"] in ("", None):
            option["attrs"]["disabled"] = True
        return option


class OrderForm(forms.ModelForm):
    model = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        required=True,
        widget=HiddenEmptyOptionSelect(attrs={"class": FORM_SELECT}),
    )
    color = forms.ModelChoiceField(
        queryset=Color.objects.none(),
        required=False,
        widget=HiddenEmptyOptionSelect(attrs={"class": FORM_SELECT}),
    )

    class Meta:
        model = ProductionOrder
        fields = ["is_etsy", "is_embroidery", "is_urgent", "comment"]
        widgets = {
            "is_etsy": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
            "is_urgent": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
            "is_embroidery": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
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
        self.fields["model"].empty_label = "—"
        self.fields["color"].empty_label = "—"
        self.fields["model"].queryset = (
            Product.objects.filter(archived_at__isnull=True).order_by("name")
        )
        self.fields["color"].queryset = (
            Color.objects.filter(
                archived_at__isnull=True,
                status__in=["in_stock", "low_stock"],
            )
            .order_by("name")
        )
        if self.instance and self.instance.pk and self.instance.variant_id:
            self.initial["model"] = self.instance.product_id
            self.initial["color"] = self.instance.variant.color_id

    def save(self, commit: bool = True):
        instance: ProductionOrder = super().save(commit=False)
        instance.product = self.cleaned_data["model"]
        color = self.cleaned_data.get("color")
        instance.variant = resolve_or_create_product_variant(
            product_id=instance.product_id,
            color_id=color.id if color else None,
        )
        if commit:
            instance.save()
        return instance


class OrderStatusUpdateForm(forms.Form):
    orders = forms.ModelMultipleChoiceField(
        queryset=ProductionOrder.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Позначити замовлення",
    )
    new_status = forms.ChoiceField(
        choices=status_choices(include_legacy=False, include_terminal=True),
        label="Новий статус",
    )
