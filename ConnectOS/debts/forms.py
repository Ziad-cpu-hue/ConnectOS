from django import forms

from vouchers.models import VoucherBatch
from .models import DebtTransaction, Reseller


class ResellerForm(forms.ModelForm):
    class Meta:
        model = Reseller
        fields = ["name", "phone", "location", "debt_limit"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "field", "placeholder": "مثال: سوبر ماركت البركة"}),
            "phone": forms.TextInput(attrs={"class": "field", "placeholder": "01xxxxxxxxx"}),
            "location": forms.TextInput(attrs={"class": "field", "placeholder": "مثال: شارع الجمهورية"}),
            "debt_limit": forms.NumberInput(attrs={"class": "field", "placeholder": "0 = بلا حد"}),
        }


class DeliverCardsForm(forms.Form):
    """تسليم كروت على الحساب — المبلغ يُحسب تلقائيًا (عدد الكروت × سعر الباقة)"""
    voucher_batch = forms.ModelChoiceField(
        queryset=VoucherBatch.objects.none(), label="دفعة الكروت",
        widget=forms.Select(attrs={"class": "field"}),
    )
    note = forms.CharField(required=False, label="ملاحظة", widget=forms.TextInput(attrs={"class": "field"}))

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields["voucher_batch"].queryset = VoucherBatch.objects.filter(company=company).select_related("plan")


class PaymentForm(forms.Form):
    amount = forms.DecimalField(
        label="المبلغ المسدَّد (جنيه)", max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "field", "placeholder": "0.00"}),
    )
    payment_method = forms.ChoiceField(
        label="طريقة السداد",
        choices=[("cash", "كاش"), ("transfer", "تحويل بنكي"), ("wallet", "محفظة إلكترونية")],
        widget=forms.Select(attrs={"class": "field"}),
    )
    note = forms.CharField(required=False, label="ملاحظة", widget=forms.TextInput(attrs={"class": "field"}))
