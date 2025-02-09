from django import forms
from .models import Order, OrderStatusHistory
from .models import Color, ProductModel

class OrderForm(forms.ModelForm):
    #color = forms.ModelChoiceField(queryset=Color.objects.all(), label="Оберіть колір")

    class Meta:
        model = Order
        fields = ['model', 'color', 'embroidery', 'urgent', 'comment']
        widgets = {
            'model': forms.Select(attrs={'class': 'form-select'}),  # Bootstrap стиль для <select>
            'color': forms.Select(attrs={'class': 'form-select'}),  # Теж Bootstrap <select>
            'urgent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),  # Checkbox стиль Bootstrap
            'embroidery': forms.CheckboxInput(attrs={'class': 'form-check-input'}),  # Checkbox
            'comment': forms.Textarea(attrs={
                'class': 'form-control',  # Bootstrap стиль для <textarea>
                'rows': 2  # Стандартний розмір для поля коментарів
            }),
        }


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

class OrderStatusUpdateForm(forms.Form):
    orders = forms.ModelMultipleChoiceField(
        queryset=Order.objects.all(),  # Всі замовлення
        widget=forms.CheckboxSelectMultiple,  # Вибір через чекбокси
        label="Вибрати замовлення"
    )
    new_status = forms.ChoiceField(
        choices=OrderStatusHistory.STATUS_CHOICES,  # Список статусів
        label="Новий статус"
    )

