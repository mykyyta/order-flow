from __future__ import annotations

from django import forms
from django.db.models import Q

from apps.materials.models import Material, MaterialUnit

from .models import Color, Product, ProductMaterial

# Design system: one class set for all form controls (see assets/tailwind/input.css)
FORM_INPUT = "form-input"
FORM_SELECT = "form-select"
FORM_CHECKBOX = "form-checkbox"


class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ["name", "code", "status"]
        labels = {"status": ""}
        widgets = {
            "name": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Колір"}),
            "code": forms.NumberInput(attrs={"class": FORM_INPUT, "placeholder": "Код"}),
            "status": forms.Select(attrs={"class": FORM_SELECT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [("", "Наявність")] + list(
            Color.AVAILABILITY_CHOICES
        )
        if not self.instance.pk:
            self.initial["status"] = ""
        self.fields["status"].required = False

    def clean_status(self):
        return self.cleaned_data.get("status") or "in_stock"

    def clean_name(self):
        name = self.cleaned_data["name"]
        return name.capitalize()


class ProductCreateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Клатч"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        return name.capitalize()


class ProductDetailForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "section",
            "is_bundle",
        ]
        labels = {
            "name": "Назва",
            "section": "Секція",
            "is_bundle": "Бандл",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": FORM_INPUT}),
            "section": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Напр. сумки"}),
            "is_bundle": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
        }


# Backwards-compat import name used in older tests/callers.
ProductForm = ProductCreateForm


class ProductMaterialForm(forms.ModelForm):
    def __init__(self, *args, product: Product | None = None, **kwargs):
        self.product = product
        super().__init__(*args, **kwargs)

        material_q = Q(archived_at__isnull=True)
        if self.instance and self.instance.pk:
            material_q |= Q(pk=self.instance.material_id)
        self.fields["material"].queryset = Material.objects.filter(material_q).order_by("name")
        self.fields["role"].required = False
        self.fields["notes"].required = False

    class Meta:
        model = ProductMaterial
        fields = ["material", "role", "quantity_per_unit", "unit", "notes"]
        labels = {
            "material": "Матеріал",
            "role": "Роль",
            "quantity_per_unit": "Норма",
            "unit": "Одиниця",
            "notes": "Нотатки",
        }
        widgets = {
            "material": forms.Select(attrs={"class": FORM_SELECT}),
            "role": forms.Select(attrs={"class": FORM_SELECT}),
            "quantity_per_unit": forms.NumberInput(
                attrs={"class": FORM_INPUT, "step": "0.001", "min": "0"}
            ),
            "unit": forms.Select(attrs={"class": FORM_SELECT}),
            "notes": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Необов'язково"}),
        }

    def clean(self):
        cleaned = super().clean()
        material = cleaned.get("material")
        role = cleaned.get("role") or ProductMaterial.Role.OTHER
        quantity_per_unit = cleaned.get("quantity_per_unit")
        unit = cleaned.get("unit")
        cleaned["role"] = role
        if (
            self.product
            and material
            and not self.instance.pk
            and ProductMaterial.objects.filter(product=self.product, material=material).exists()
        ):
            self.add_error("material", "Для цієї моделі цей матеріал вже додано.")
            return cleaned

        if unit and not quantity_per_unit:
            self.add_error("quantity_per_unit", "Вкажи норму або прибери одиницю.")
            return cleaned
        if quantity_per_unit and not unit:
            self.add_error("unit", "Обери одиницю виміру.")
            return cleaned

        if not self.product or not material or not role:
            return cleaned

        if role == ProductMaterial.Role.SECONDARY:
            if self.product.primary_material_id is None:
                self.add_error("role", "Спочатку обери основний матеріал.")
                return cleaned
            if self.product.primary_material_id == material.pk:
                self.add_error("role", "Другорядний матеріал має відрізнятись від основного.")
                return cleaned

        if unit and unit not in {choice[0] for choice in MaterialUnit.choices}:
            self.add_error("unit", "Невірна одиниця.")
            return cleaned

        return cleaned
