from django import forms

from apps.materials.models import Material

FORM_INPUT = "form-input"


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": FORM_INPUT, "placeholder": "Матеріал"}),
        }

    def clean_name(self) -> str:
        name: str = self.cleaned_data["name"]
        return name.capitalize()

