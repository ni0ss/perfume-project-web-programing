from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import get_language


class RegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=160)
    phone = forms.CharField(max_length=30, widget=forms.TelInput(attrs={'autocomplete': 'tel', 'dir': 'ltr'}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'autocomplete': 'address-level2'}))
    address = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'autocomplete': 'street-address'}))
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(['username', 'email', 'full_name', 'phone', 'city', 'address', 'password1', 'password2'])
        is_arabic = get_language() == 'ar'
        labels = {
            'full_name': ('الاسم الكامل', 'Full name'),
            'phone': ('رقم الجوال', 'Phone number'),
            'city': ('المدينة', 'City'),
            'address': ('العنوان بالتفصيل', 'Delivery address'),
            'username': ('اسم المستخدم', 'Username'),
            'email': ('البريد الإلكتروني', 'Email address'),
            'password1': ('كلمة المرور', 'Password'),
            'password2': ('تأكيد كلمة المرور', 'Confirm password'),
        }
        for field_name, (arabic, english) in labels.items():
            self.fields[field_name].label = arabic if is_arabic else english
        self.fields['full_name'].widget.attrs['autocomplete'] = 'name'
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
