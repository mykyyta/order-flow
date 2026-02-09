"""Form tests for materials app."""
import pytest

from apps.materials.forms import MaterialForm


@pytest.mark.django_db
class TestMaterialForm:
    def test_clean_name_capitalizes(self):
        form = MaterialForm(data={"name": "genuine leather"})
        assert form.is_valid()
        assert form.cleaned_data["name"] == "Genuine leather"
