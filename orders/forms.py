from django import forms
from .models import Order
from .models import Color, ProductModel

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['model', 'color', 'embroidery', 'urgent', 'comment']


class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ['name', 'code', 'availability_status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.NumberInput(attrs={'class': 'form-control'}),
            'availability_status': forms.Select(attrs={'class': 'form-control'}),
        }

class ProductModelForm(forms.ModelForm):
    class Meta:
        model = ProductModel
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }