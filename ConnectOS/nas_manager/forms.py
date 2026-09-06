from django import forms

from .models import NASServer


class NASServerForm(forms.ModelForm):
    class Meta:
        model = NASServer
        fields = ["name", "ip_address", "secret", "api_username", "api_password", "api_port", "region", "latitude", "longitude"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "field", "placeholder": "مثال: عمود شارع النصر"}),
            "ip_address": forms.TextInput(attrs={"class": "field", "placeholder": "192.168.1.1"}),
            "secret": forms.TextInput(attrs={"class": "field", "placeholder": "المفتاح السري المشترك (RADIUS)"}),
            "api_username": forms.TextInput(attrs={"class": "field", "placeholder": "admin"}),
            "api_password": forms.PasswordInput(attrs={"class": "field", "placeholder": "باسورد RouterOS API"}, render_value=True),
            "api_port": forms.NumberInput(attrs={"class": "field"}),
            "region": forms.TextInput(attrs={"class": "field", "placeholder": "مثال: حي المعادي"}),
            "latitude": forms.NumberInput(attrs={"class": "field"}),
            "longitude": forms.NumberInput(attrs={"class": "field"}),
        }
