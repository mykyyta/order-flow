from django import forms
from .models import Order, OrderStatusHistory
from .models import Color, ProductModel

class OrderForm(forms.ModelForm):

    class Meta:
        model = Order
        fields = ['model', 'color', 'etsy', 'embroidery', 'urgent', 'comment']
        widgets = {
            'model': forms.Select(attrs={
                'class': 'block w-full rounded-md border border-slate-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm',
            }),
            'color': forms.Select(attrs={
                'class': 'block w-full rounded-md border border-slate-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm',
            }),
            'etsy': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border border-slate-300 text-teal-600 focus:ring-teal-500',
            }),
            'urgent': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border border-slate-300 text-teal-600 focus:ring-teal-500',
            }),
            'embroidery': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border border-slate-300 text-teal-600 focus:ring-teal-500',
            }),
            'comment': forms.Textarea(attrs={
                'class': 'block w-full rounded-md border border-slate-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm',
                'rows': 2,
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
            'name': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border border-slate-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm',
            }),
            'code': forms.NumberInput(attrs={
                'class': 'block w-full rounded-md border border-slate-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm',
            }),
            'availability_status': forms.Select(attrs={
                'class': 'block w-full rounded-md border border-slate-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        return name.capitalize()


class ProductModelForm(forms.ModelForm):
    class Meta:
        model = ProductModel
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border border-slate-300 shadow-sm focus:border-teal-500 focus:ring-teal-500 sm:text-sm',
            }),
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

