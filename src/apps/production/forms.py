from django import forms
from django.db.models import Q

from apps.catalog.models import Product
from apps.catalog.variants import resolve_or_create_variant
from apps.materials.models import MaterialColor
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
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        required=True,
        widget=HiddenEmptyOptionSelect(attrs={"class": FORM_SELECT}),
    )
    primary_material_color = forms.ModelChoiceField(
        queryset=MaterialColor.objects.none(),
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
        self.fields["product"].empty_label = "—"
        self.fields["primary_material_color"].empty_label = "—"

        product_filters = Q(archived_at__isnull=True)
        if self.instance and self.instance.pk:
            product_filters |= Q(pk=self.instance.product_id)
        self.fields["product"].queryset = Product.objects.filter(product_filters).order_by("name")

        selected_product: Product | None = None
        if self.is_bound:
            raw_product_id = self.data.get(self.add_prefix("product"))
            if raw_product_id:
                selected_product = Product.objects.filter(pk=raw_product_id).first()
        elif self.instance and self.instance.pk:
            selected_product = self.instance.product

        self.fields["primary_material_color"].queryset = self._primary_color_queryset(
            product=selected_product
        )
        if self.instance and self.instance.pk and self.instance.variant_id:
            self.initial["product"] = self.instance.product_id
            self.initial["primary_material_color"] = self.instance.variant.primary_material_color_id
            if self.instance.variant.primary_material_color_id:
                self.fields["primary_material_color"].queryset = (
                    self.fields["primary_material_color"].queryset
                    | MaterialColor.objects.filter(pk=self.instance.variant.primary_material_color_id)
                )
                self.fields["primary_material_color"].queryset = self.fields[
                    "primary_material_color"
                ].queryset.order_by("name")

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        primary_material_color = cleaned_data.get("primary_material_color")
        if not product:
            return cleaned_data

        available_colors = self._primary_color_queryset(product=product)
        if not product.primary_material_id:
            if primary_material_color is not None:
                self.add_error(
                    "primary_material_color",
                    "Для цієї моделі основний колір недоступний.",
                )
            return cleaned_data

        if primary_material_color and primary_material_color.material_id != product.primary_material_id:
            self.add_error(
                "primary_material_color",
                "Обраний колір не належить до матеріалу моделі.",
            )
            return cleaned_data

        if available_colors.exists() and primary_material_color is None:
            self.add_error(
                "primary_material_color",
                "Обери основний колір для цієї моделі.",
            )

        return cleaned_data

    @staticmethod
    def _primary_color_queryset(*, product: Product | None):
        if product is None:
            return MaterialColor.objects.filter(archived_at__isnull=True).order_by("name")
        if not product.primary_material_id:
            return MaterialColor.objects.none()
        return MaterialColor.objects.filter(
            material_id=product.primary_material_id,
            archived_at__isnull=True,
        ).order_by("name")

    def save(self, commit: bool = True):
        instance: ProductionOrder = super().save(commit=False)
        instance.product = self.cleaned_data["product"]
        primary_material_color = self.cleaned_data.get("primary_material_color")
        instance.variant = resolve_or_create_variant(
            product_id=instance.product_id,
            primary_material_color_id=(
                primary_material_color.id if primary_material_color else None
            ),
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
