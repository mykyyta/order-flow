from django import forms
from .models import Order, OrderStatusHistory
from .models import Color, ProductModel

class OrderForm(forms.ModelForm):

    class Meta:
        model = Order
        fields = ['model', 'color', 'etsy', 'embroidery', 'urgent', 'comment']
        widgets = {
            'model': forms.Select(attrs={'class': 'form-select'}),
            'color': forms.Select(attrs={'class': 'form-select'}),
            'etsy': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'urgent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'embroidery': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['color'].queryset = Color.objects.filter(
            availability_status__in=['in_stock', 'low_stock']
        )



class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ['name', 'code', 'availability_status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.NumberInput(attrs={'class': 'form-control'}),
            'availability_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        return name.capitalize()


class ProductModelForm(forms.ModelForm):
    class Meta:
        model = ProductModel
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        return name.capitalize()


class OrderStatusUpdateForm(forms.Form):
    orders = forms.ModelMultipleChoiceField(
        queryset=Order.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Вибрати замовлення"
    )
    new_status = forms.ChoiceField(
        choices=OrderStatusHistory.STATUS_CHOICES,
        label="Новий статус"
    )

