from __future__ import annotations

from django import forms
from django.db.models import Q

from apps.materials.models import Material, MaterialUnit

from .models import BundleComponent, Color, Product, ProductMaterial

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
        self.fields["status"].choices = [("", "Наявність")] + list(Color.AVAILABILITY_CHOICES)
        if not self.instance.pk:
            self.initial["status"] = ""
        self.fields["status"].required = False

    def clean_status(self):
        return self.cleaned_data.get("status") or "in_stock"

    def clean_name(self):
        name = self.cleaned_data["name"]
        return name.capitalize()


class ProductCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Backwards-compatible: old callers/tests post only "name". Default kind to "Продукт".
        self.fields["kind"].required = False
        self.fields["kind"].choices = [
            (Product.Kind.STANDARD, Product.Kind.STANDARD.label),
            (Product.Kind.BUNDLE, Product.Kind.BUNDLE.label),
            (Product.Kind.COMPONENT, Product.Kind.COMPONENT.label),
        ]

    class Meta:
        model = Product
        fields = ["kind", "name"]
        widgets = {
            "kind": forms.Select(attrs={"class": FORM_SELECT}),
            "name": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Клатч"}),
        }

    def clean_kind(self):
        return self.cleaned_data.get("kind") or Product.Kind.STANDARD

    def clean_name(self):
        name = self.cleaned_data["name"]
        return name.capitalize()


class ProductDetailForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "section",
            "kind",
            "allows_embroidery",
        ]
        labels = {
            "name": "Назва",
            "section": "Секція",
            "kind": "Тип",
            "allows_embroidery": "Вишивка",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": FORM_INPUT}),
            "section": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Напр. сумки"}),
            "kind": forms.Select(attrs={"class": FORM_SELECT}),
            "allows_embroidery": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # UI order: продукт, комплект, компонент.
        self.fields["kind"].choices = [
            (Product.Kind.STANDARD, Product.Kind.STANDARD.label),
            (Product.Kind.BUNDLE, Product.Kind.BUNDLE.label),
            (Product.Kind.COMPONENT, Product.Kind.COMPONENT.label),
        ]

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        if not self.instance or not self.instance.pk or not kind:
            return cleaned

        current_kind = self.instance.kind
        if kind == current_kind:
            return cleaned

        has_materials = ProductMaterial.objects.filter(product=self.instance).exists()
        has_components = BundleComponent.objects.filter(bundle=self.instance).exists()

        # If the product already has materials, type changes are blocked to prevent
        # confusing/invalid mixes. Remove materials first.
        if has_materials and current_kind in (Product.Kind.STANDARD, Product.Kind.COMPONENT):
            self.add_error("kind", "Спочатку видали матеріали продукту.")
            return cleaned

        # If the product is a bundle (комплект), you must remove components first before changing type.
        if current_kind == Product.Kind.BUNDLE and has_components:
            self.add_error("kind", "Спочатку видали компоненти комплекту.")
            return cleaned

        # Additional guard: do not allow switching to bundle while materials exist.
        if kind == Product.Kind.BUNDLE and has_materials:
            self.add_error(
                "kind", "Для комплекту матеріали не задаються. Спочатку видали матеріали."
            )
            return cleaned

        return cleaned

    def save(self, commit=True):
        product: Product = super().save(commit=False)

        # Normalize fields that do not apply to bundles.
        if product.kind == Product.Kind.BUNDLE:
            product.allows_embroidery = False
            product.primary_material = None
            product.secondary_material = None

        if commit:
            product.save()
            self.save_m2m()
        return product


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

        if self.product and self.product.kind == Product.Kind.BUNDLE:
            self.add_error(
                "material",
                "Для комплектів матеріали не задаються. Додай матеріали для компонентів комплекту.",
            )
            return cleaned

        if (
            self.product
            and material
            and not self.instance.pk
            and ProductMaterial.objects.filter(product=self.product, material=material).exists()
        ):
            self.add_error("material", "Для цього продукту цей матеріал вже додано.")
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


class BundleComponentForm(forms.ModelForm):
    def __init__(self, *args, bundle: Product | None = None, **kwargs):
        self.bundle = bundle
        super().__init__(*args, **kwargs)

        component_q = Q(archived_at__isnull=True) & (
            Q(kind=Product.Kind.STANDARD) | Q(kind=Product.Kind.COMPONENT)
        )
        if self.instance and self.instance.pk:
            component_q |= Q(pk=self.instance.component_id)
        self.fields["component"].queryset = Product.objects.filter(component_q).order_by("name")

    class Meta:
        model = BundleComponent
        fields = ["component", "quantity", "is_primary", "is_required", "group"]
        labels = {
            "component": "Компонент",
            "quantity": "Кількість",
            "is_primary": "Основний",
            "is_required": "Обов'язковий",
            "group": "Група",
        }
        widgets = {
            "component": forms.Select(attrs={"class": FORM_SELECT}),
            "quantity": forms.NumberInput(attrs={"class": FORM_INPUT, "min": "1", "step": "1"}),
            "is_primary": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
            "is_required": forms.CheckboxInput(attrs={"class": FORM_CHECKBOX}),
            "group": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Необов'язково"}),
        }

    def clean(self):
        cleaned = super().clean()
        component = cleaned.get("component")
        if self.bundle is None:
            return cleaned

        if self.bundle.kind != Product.Kind.BUNDLE:
            self.add_error("component", "Компоненти можна додавати лише до комплектів.")
            return cleaned

        if component and component.kind == Product.Kind.BUNDLE:
            self.add_error("component", "Компонентом не може бути комплект.")
            return cleaned
        if component and component.pk == self.bundle.pk:
            self.add_error("component", "Комплект не може містити сам себе.")
            return cleaned

        if (
            component
            and (not self.instance.pk)
            and BundleComponent.objects.filter(bundle=self.bundle, component=component).exists()
        ):
            self.add_error("component", "Цей компонент вже додано.")
            return cleaned

        return cleaned
