from django import forms

from plans.models import Plan
from .models import TopupBatch, VoucherBatch, VoucherTemplate


class VoucherBatchForm(forms.ModelForm):
    class Meta:
        model = VoucherBatch
        fields = ["plan", "template", "quantity"]
        widgets = {
            "plan": forms.Select(attrs={"class": "field"}),
            "template": forms.Select(attrs={"class": "field"}),
            "quantity": forms.NumberInput(attrs={"class": "field", "placeholder": "مثال: 100"}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields["plan"].queryset = Plan.objects.filter(company=company, is_active=True)
            self.fields["template"].queryset = VoucherTemplate.objects.filter(company=company)
        self.fields["template"].required = False


class VoucherTemplateForm(forms.ModelForm):
    class Meta:
        model = VoucherTemplate
        fields = ["name", "primary_color", "secondary_color", "logo_text", "support_phone",
                  "background_image", "show_qr", "is_default"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "field"}),
            "primary_color": forms.TextInput(attrs={"class": "field", "type": "color"}),
            "secondary_color": forms.TextInput(attrs={"class": "field", "type": "color"}),
            "logo_text": forms.TextInput(attrs={"class": "field"}),
            "support_phone": forms.TextInput(attrs={"class": "field"}),
        }


class TopupBatchForm(forms.ModelForm):
    """توليد دفعة كروت شحن رصيد — منفصلة تمامًا عن كروت الهوت سبوت، ومش
    مربوطة بباقة أو سيرفر معين."""

    class Meta:
        model = TopupBatch
        fields = ["amount", "quantity"]
        widgets = {
            "amount": forms.NumberInput(attrs={"class": "field", "placeholder": "مثال: 20"}),
            "quantity": forms.NumberInput(attrs={"class": "field", "placeholder": "مثال: 100"}),
        }
