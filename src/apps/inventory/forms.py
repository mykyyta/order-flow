from __future__ import annotations

from decimal import Decimal

from django import forms
from django.db.models.functions import Lower

from apps.catalog.models import Product
from apps.materials.models import Material, MaterialColor

FORM_INPUT = "form-input"
FORM_SELECT = "form-select"
FORM_TEXTAREA = "form-textarea"


class MaterialStockAdjustmentForm(forms.Form):
    material = forms.ModelChoiceField(
        queryset=Material.objects.filter(archived_at__isnull=True).order_by("name"),
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Матеріал",
    )
    material_color = forms.ModelChoiceField(
        queryset=MaterialColor.objects.filter(archived_at__isnull=True)
        .select_related("material")
        .order_by("material__name", "name"),
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Колір (необов'язково)",
    )
    quantity = forms.DecimalField(
        min_value=Decimal("0.001"),
        decimal_places=3,
        widget=forms.NumberInput(attrs={"class": FORM_INPUT, "step": "0.001"}),
        label="Кількість",
    )

    def clean(self) -> dict:
        cleaned = super().clean()
        material: Material | None = cleaned.get("material")
        material_color: MaterialColor | None = cleaned.get("material_color")
        if material and material_color and material_color.material_id != material.id:
            self.add_error("material_color", "Колір має належати вибраному матеріалу.")
        if material and material_color is None:
            if material.colors.filter(archived_at__isnull=True).exists():
                self.add_error("material_color", "Обери колір.")
        return cleaned


class MaterialAdjustmentSelectForm(forms.Form):
    material = forms.ModelChoiceField(
        queryset=Material.objects.filter(archived_at__isnull=True).order_by("name"),
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Матеріал",
    )


class ProductAdjustmentSelectForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(archived_at__isnull=True)
        .exclude(kind=Product.Kind.BUNDLE)
        .order_by("name"),
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Виріб / компонент",
    )


class ProductStockAdjustmentForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(
            archived_at__isnull=True,
        )
        .exclude(kind=Product.Kind.BUNDLE)
        .order_by("name"),
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Виріб",
    )
    primary_material_color = forms.ModelChoiceField(
        queryset=MaterialColor.objects.filter(archived_at__isnull=True)
        .select_related("material")
        .order_by("material__name", "name"),
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Основний колір",
    )
    secondary_material_color = forms.ModelChoiceField(
        queryset=MaterialColor.objects.filter(archived_at__isnull=True)
        .select_related("material")
        .order_by("material__name", "name"),
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Другорядний колір (необов'язково)",
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={"class": FORM_INPUT, "min": "1", "step": "1"}),
        label="Кількість",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": FORM_TEXTAREA, "rows": 2}),
        label="Коментар (необов'язково)",
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        product = None
        raw_product_id = None
        if self.is_bound:
            raw_product_id = self.data.get(self.add_prefix("product"))
        elif self.initial.get("product"):
            raw_product_id = self.initial.get("product")

        if raw_product_id:
            try:
                product = Product.objects.filter(pk=int(raw_product_id)).first()
            except (TypeError, ValueError):
                product = None

        self.fields["primary_material_color"].queryset = self._primary_color_queryset(product=product)
        self.fields["secondary_material_color"].queryset = self._secondary_color_queryset(product=product)

    def clean(self) -> dict:
        cleaned = super().clean()
        product: Product | None = cleaned.get("product")
        primary: MaterialColor | None = cleaned.get("primary_material_color")
        secondary: MaterialColor | None = cleaned.get("secondary_material_color")

        if product is None:
            return cleaned

        if product.kind == Product.Kind.BUNDLE:
            self.add_error("product", "Комплекти не обліковуються на складі.")
            return cleaned

        requires_primary = bool(
            product.primary_material_id
            and MaterialColor.objects.filter(
                material_id=product.primary_material_id,
                archived_at__isnull=True,
            ).exists()
        )

        if not product.primary_material_id:
            if primary is not None:
                self.add_error("primary_material_color", "Для цього виробу основний колір недоступний.")
            if secondary is not None:
                self.add_error(
                    "secondary_material_color",
                    "Для цього виробу другорядний колір недоступний.",
                )
            return cleaned

        if requires_primary and primary is None:
            self.add_error("primary_material_color", "Обери основний колір.")

        if primary and product.primary_material_id and primary.material_id != product.primary_material_id:
            self.add_error("primary_material_color", "Колір не відповідає основному матеріалу виробу.")

        if secondary and not product.secondary_material_id:
            self.add_error("secondary_material_color", "Для цього виробу немає другорядного матеріалу.")
        if secondary and product.secondary_material_id and secondary.material_id != product.secondary_material_id:
            self.add_error(
                "secondary_material_color",
                "Колір не відповідає другорядному матеріалу виробу.",
            )
        if secondary and primary is None:
            self.add_error("primary_material_color", "Спочатку обери основний колір.")

        return cleaned

    @staticmethod
    def _primary_color_queryset(*, product: Product | None):
        if product is None:
            return MaterialColor.objects.filter(archived_at__isnull=True).order_by(Lower("name"), "name")
        if not product.primary_material_id:
            return MaterialColor.objects.none()
        return MaterialColor.objects.filter(
            material_id=product.primary_material_id,
            archived_at__isnull=True,
        ).order_by(Lower("name"), "name")

    @staticmethod
    def _secondary_color_queryset(*, product: Product | None):
        if product is None:
            return MaterialColor.objects.filter(archived_at__isnull=True).order_by(Lower("name"), "name")
        if not product.secondary_material_id:
            return MaterialColor.objects.none()
        return MaterialColor.objects.filter(
            material_id=product.secondary_material_id,
            archived_at__isnull=True,
        ).order_by(Lower("name"), "name")
