from django import forms

from .models import Color, ProductModel

# Design system: one class set for all form controls (see assets/tailwind/input.css)
FORM_INPUT = "form-input"
FORM_SELECT = "form-select"


class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ["name", "code", "availability_status"]
        labels = {"availability_status": ""}
        widgets = {
            "name": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Колір"}),
            "code": forms.NumberInput(attrs={"class": FORM_INPUT, "placeholder": "Код"}),
            "availability_status": forms.Select(attrs={"class": FORM_SELECT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["availability_status"].choices = [("", "Наявність")] + list(
            Color.AVAILABILITY_CHOICES
        )
        if not self.instance.pk:
            self.initial["availability_status"] = ""
        self.fields["availability_status"].required = False

    def clean_availability_status(self):
        return self.cleaned_data.get("availability_status") or "in_stock"

    def clean_name(self):
        name = self.cleaned_data["name"]
        return name.capitalize()


class ProductModelForm(forms.ModelForm):
    class Meta:
        model = ProductModel
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Клатч"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        return name.capitalize()
