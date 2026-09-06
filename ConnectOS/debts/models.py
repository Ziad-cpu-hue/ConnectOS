from django.db import models
from django.db.models import Sum

from core.models import Company, SoftDeleteModel


class Reseller(SoftDeleteModel):
    """الموزّع - صاحب سوبر ماركت أو محل بيبيع الكروت"""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="resellers", verbose_name="الشركة")
    name = models.CharField("اسم الموزع", max_length=200)
    phone = models.CharField("رقم الهاتف", max_length=20)
    location = models.CharField("الموقع / المنطقة", max_length=200, blank=True)
    debt_limit = models.DecimalField("الحد الأقصى المسموح للدين", max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField("نشط", default=True)
    created_at = models.DateTimeField("تاريخ الإضافة", auto_now_add=True)

    class Meta:
        verbose_name = "موزّع"
        verbose_name_plural = "الموزعون"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def current_debt(self):
        """الدين الحالي = مجموع الكروت المُسلَّمة على الحساب - مجموع السدادات"""
        owed = self.transactions.filter(type="card_delivery").aggregate(s=Sum("amount"))["s"] or 0
        paid = self.transactions.filter(type="payment").aggregate(s=Sum("amount"))["s"] or 0
        return owed - paid

    @property
    def is_over_limit(self):
        return self.debt_limit > 0 and self.current_debt > self.debt_limit


class DebtTransaction(models.Model):
    """كل حركة مالية على حساب الموزع: تسليم كروت على الحساب، أو سداد دفعة"""

    TYPE_CHOICES = [
        ("card_delivery", "تسليم كروت على الحساب"),
        ("payment", "سداد دفعة"),
        ("manual_adjustment", "تعديل يدوي"),
    ]

    reseller = models.ForeignKey(Reseller, on_delete=models.CASCADE, related_name="transactions", verbose_name="الموزّع")
    type = models.CharField("نوع الحركة", max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField("المبلغ (جنيه)", max_digits=10, decimal_places=2)
    voucher_batch = models.ForeignKey(
        "vouchers.VoucherBatch", on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="دفعة الكروت المرتبطة",
    )
    payment_method = models.CharField("طريقة السداد", max_length=50, blank=True)
    note = models.TextField("ملاحظة", blank=True)
    created_by = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True, verbose_name="سُجّلت بواسطة")
    created_at = models.DateTimeField("التاريخ", auto_now_add=True)

    class Meta:
        verbose_name = "حركة دين"
        verbose_name_plural = "حركات الديون"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reseller.name} - {self.get_type_display()} - {self.amount} ج"
