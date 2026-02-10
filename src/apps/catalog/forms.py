from django import forms

from .models import Color, Product

# Design system: one class set for all form controls (see assets/tailwind/input.css)
FORM_INPUT = "form-input"
FORM_SELECT = "form-select"


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


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Клатч"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        return name.capitalize()
