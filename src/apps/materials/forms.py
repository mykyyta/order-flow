from __future__ import annotations

from decimal import Decimal

from django import forms

from apps.materials.models import (
    Material,
    MaterialColor,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequest,
    PurchaseRequestLine,
    Supplier,
    SupplierMaterialOffer,
)

FORM_INPUT = "form-input"
FORM_SELECT = "form-select"
FORM_TEXTAREA = "form-textarea"


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ["name", "stock_unit"]
        widgets = {
            "name": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Матеріал"}),
            "stock_unit": forms.Select(attrs={"class": FORM_SELECT}),
        }

    def clean_name(self) -> str:
        name: str = self.cleaned_data["name"]
        return name.capitalize()


class MaterialColorForm(forms.ModelForm):
    class Meta:
        model = MaterialColor
        fields = ["code", "name"]
        widgets = {
            "code": forms.NumberInput(attrs={"class": FORM_INPUT, "placeholder": "01"}),
            "name": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Назва кольору"}),
        }

    def clean_name(self) -> str:
        name: str = self.cleaned_data["name"]
        return name.capitalize()


class PurchaseOrderFilterForm(forms.Form):
    status = forms.ChoiceField(
        required=False,
        choices=[("", "Усі")] + list(PurchaseOrder.Status.choices),
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Статус",
    )


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["supplier", "external_ref", "tracking_number", "expected_at", "notes", "status"]
        widgets = {
            "supplier": forms.Select(attrs={"class": FORM_SELECT}),
            "external_ref": forms.TextInput(attrs={"class": FORM_INPUT}),
            "tracking_number": forms.TextInput(attrs={"class": FORM_INPUT}),
            "expected_at": forms.DateInput(attrs={"class": FORM_INPUT, "type": "date"}),
            "notes": forms.Textarea(attrs={"class": FORM_TEXTAREA, "rows": 3}),
            "status": forms.Select(attrs={"class": FORM_SELECT}),
        }


class PurchaseOrderEditForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["expected_at", "notes"]
        widgets = {
            "expected_at": forms.DateInput(attrs={"class": FORM_INPUT, "type": "date"}),
            "notes": forms.Textarea(attrs={"class": FORM_TEXTAREA, "rows": 3}),
        }


class PurchaseOrderStartForm(forms.Form):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(archived_at__isnull=True).order_by("name"),
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Постачальник",
    )


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact_name", "phone", "email", "website", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Назва постачальника"}),
            "contact_name": forms.TextInput(attrs={"class": FORM_INPUT}),
            "phone": forms.TextInput(attrs={"class": FORM_INPUT}),
            "email": forms.EmailInput(attrs={"class": FORM_INPUT}),
            "website": forms.URLInput(attrs={"class": FORM_INPUT}),
            "notes": forms.Textarea(attrs={"class": FORM_TEXTAREA, "rows": 3}),
        }


class SupplierMaterialOfferForm(forms.ModelForm):
    class Meta:
        model = SupplierMaterialOffer
        fields = [
            "supplier",
            "material_color",
            "title",
            "sku",
            "url",
            "price_per_unit",
            "notes",
        ]
        widgets = {
            "supplier": forms.Select(attrs={"class": FORM_SELECT}),
            "material_color": forms.Select(attrs={"class": FORM_SELECT}),
            "title": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Назва у магазині"}),
            "sku": forms.TextInput(attrs={"class": FORM_INPUT}),
            "url": forms.URLInput(attrs={"class": FORM_INPUT}),
            "price_per_unit": forms.NumberInput(attrs={"class": FORM_INPUT, "step": "0.01", "min": "0"}),
            "notes": forms.Textarea(attrs={"class": FORM_TEXTAREA, "rows": 2}),
        }

    def __init__(self, *args, material: Material | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._material = material
        if material is not None:
            self.fields["material_color"].queryset = material.colors.filter(archived_at__isnull=True).order_by(
                "name",
                "code",
                "id",
            )

    def clean(self) -> dict:
        cleaned = super().clean()
        material = self._material
        material_color: MaterialColor | None = cleaned.get("material_color")
        if material is not None:
            has_colors = material.colors.filter(archived_at__isnull=True).exists()
            if has_colors and material_color is None:
                self.add_error("material_color", "Обери колір.")
        return cleaned

    def clean_title(self) -> str:
        title: str = (self.cleaned_data.get("title") or "").strip()
        if not title:
            raise forms.ValidationError("Вкажи назву позиції у постачальника.")
        return title


class SupplierMaterialOfferStartForm(forms.Form):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(archived_at__isnull=True).order_by("name"),
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Постачальник",
    )
    material = forms.ModelChoiceField(
        queryset=Material.objects.filter(archived_at__isnull=True).order_by("name"),
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Матеріал",
    )


class PurchaseAddFromOfferForm(forms.Form):
    quantity = forms.DecimalField(
        min_value=Decimal("0.001"),
        decimal_places=3,
        widget=forms.NumberInput(attrs={"class": FORM_INPUT, "step": "0.001", "min": "0.001"}),
        label="Кількість",
    )
    unit_price = forms.DecimalField(
        required=False,
        min_value=Decimal("0.00"),
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": FORM_INPUT, "step": "0.01", "min": "0"}),
        label="Ціна за одиницю",
    )


class PurchaseOrderLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderLine
        fields = ["material", "material_color", "quantity", "unit_price", "notes"]
        widgets = {
            "material": forms.Select(attrs={"class": FORM_SELECT}),
            "material_color": forms.Select(attrs={"class": FORM_SELECT}),
            "quantity": forms.NumberInput(attrs={"class": FORM_INPUT, "step": "0.001", "min": "0.001"}),
            "unit_price": forms.NumberInput(attrs={"class": FORM_INPUT, "step": "0.01", "min": "0"}),
            "notes": forms.TextInput(attrs={"class": FORM_INPUT}),
        }

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


class PurchaseOrderLineReceiveForm(forms.Form):
    quantity = forms.DecimalField(
        min_value=Decimal("0.001"),
        decimal_places=3,
        widget=forms.NumberInput(attrs={"class": FORM_INPUT, "step": "0.001"}),
        label="Кількість",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": FORM_TEXTAREA, "rows": 2}),
        label="Коментар",
    )


class PurchaseOrderStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=list(PurchaseOrder.Status.choices),
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Статус",
    )


class PurchaseRequestForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequest
        fields = ["notes", "status"]
        widgets = {
            "notes": forms.Textarea(attrs={"class": FORM_TEXTAREA, "rows": 3}),
            "status": forms.Select(attrs={"class": FORM_SELECT}),
        }


class PurchaseRequestEditForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequest
        fields = ["notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"class": FORM_TEXTAREA, "rows": 3}),
        }


class PurchaseRequestLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequestLine
        fields = ["material", "material_color", "requested_quantity", "notes", "status"]
        widgets = {
            "material": forms.Select(attrs={"class": FORM_SELECT}),
            "material_color": forms.Select(attrs={"class": FORM_SELECT}),
            "requested_quantity": forms.NumberInput(
                attrs={"class": FORM_INPUT, "step": "0.001", "min": "0.001"}
            ),
            "notes": forms.Textarea(attrs={"class": FORM_TEXTAREA, "rows": 2}),
            "status": forms.Select(attrs={"class": FORM_SELECT}),
        }

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


class PurchaseRequestLineOrderForm(forms.Form):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(archived_at__isnull=True).order_by("name"),
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Постачальник",
    )
    purchase_order = forms.ModelChoiceField(
        queryset=PurchaseOrder.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT}),
        label="Додати в замовлення",
        help_text="Якщо не вибрати, буде створено нову чернетку.",
    )
    quantity = forms.DecimalField(
        min_value=Decimal("0.001"),
        decimal_places=3,
        widget=forms.NumberInput(attrs={"class": FORM_INPUT, "step": "0.001", "min": "0.001"}),
        label="Кількість",
    )
    unit_price = forms.DecimalField(
        required=False,
        min_value=Decimal("0.00"),
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": FORM_INPUT, "step": "0.01", "min": "0"}),
        label="Ціна за одиницю",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": FORM_TEXTAREA, "rows": 2}),
        label="Коментар",
    )

    def __init__(self, *args, supplier_id: int | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        supplier_from_data = None
        if self.is_bound:
            supplier_from_data = self.data.get(self.add_prefix("supplier"))
        supplier_pk = supplier_id or (int(supplier_from_data) if supplier_from_data and supplier_from_data.isdigit() else None)

        if supplier_pk:
            self.fields["purchase_order"].queryset = PurchaseOrder.objects.filter(
                supplier_id=supplier_pk,
                status=PurchaseOrder.Status.DRAFT,
            ).order_by("-created_at")
