from django import forms

from .models import Subscriber, SubscriberGroup


class SubscriberForm(forms.ModelForm):
    class Meta:
        model = Subscriber
        fields = ["full_name", "phone", "username", "password", "plan", "group", "mac_lock",
                  "status", "expires_at", "can_self_renew", "can_self_topup"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "field", "placeholder": "مثال: أحمد محمود"}),
            "phone": forms.TextInput(attrs={"class": "field", "placeholder": "01xxxxxxxxx"}),
            "username": forms.TextInput(attrs={"class": "field", "placeholder": "اسم الدخول على الهوت سبوت"}),
            "password": forms.TextInput(attrs={"class": "field", "placeholder": "كلمة المرور"}),
            "plan": forms.Select(attrs={"class": "field"}),
            "group": forms.Select(attrs={"class": "field"}),
            "mac_lock": forms.TextInput(attrs={"class": "field", "placeholder": "AA:BB:CC:DD:EE:FF (اختياري)"}),
            "status": forms.Select(attrs={"class": "field"}),
            "expires_at": forms.DateTimeInput(attrs={"class": "field", "type": "datetime-local"}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields["plan"].queryset = self.fields["plan"].queryset.filter(company=company, is_active=True)
            self.fields["group"].queryset = SubscriberGroup.objects.filter(company=company)
            self.fields["group"].required = False


class SubscriberGroupForm(forms.ModelForm):
    class Meta:
        model = SubscriberGroup
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"class": "field", "placeholder": "مثال: شارع النصر"})}
