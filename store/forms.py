from django import forms

from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('full_name', 'phone', 'city', 'address', 'notes')
        labels = {
            'full_name': 'الاسم الكامل',
            'phone': 'رقم الجوال',
            'city': 'المدينة',
            'address': 'العنوان بالتفصيل',
            'notes': 'ملاحظات التوصيل (اختياري)',
        }
        widgets = {
            'full_name': forms.TextInput(attrs={'autocomplete': 'name'}),
            'phone': forms.TelInput(attrs={'autocomplete': 'tel', 'dir': 'ltr'}),
            'city': forms.TextInput(attrs={'autocomplete': 'address-level2'}),
            'address': forms.TextInput(attrs={'autocomplete': 'street-address'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
