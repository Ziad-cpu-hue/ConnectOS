from django import forms

from .models import Plan


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ["name", "quota_mb", "duration_days", "speed_limit_kbps", "price", "is_active",
                  "speed_equation_enabled", "allow_open_speed"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "field", "placeholder": "مثال: باقة 3 أيام"}),
            "quota_mb": forms.NumberInput(attrs={"class": "field", "placeholder": "1700"}),
            "duration_days": forms.NumberInput(attrs={"class": "field", "placeholder": "3"}),
            "speed_limit_kbps": forms.NumberInput(attrs={"class": "field", "placeholder": "اختياري"}),
            "price": forms.NumberInput(attrs={"class": "field", "placeholder": "10"}),
        }
