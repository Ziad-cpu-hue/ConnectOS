from django.db import models

from core.models import Company


class PaymentTransaction(models.Model):
    """معاملة دفع — إما شحن رصيد اشتراك الشركة في المنصة، أو تجديد اشتراك
    مشترك نهائي عن طريق بوابة العميل (لو subscriber محدد)."""

    STATUS_CHOICES = [
        ("pending", "قيد الانتظار"),
        ("paid", "تم الدفع"),
        ("failed", "فشلت"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="payment_transactions")
    subscriber = models.ForeignKey(
        "subscribers.Subscriber", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="payments", help_text="لو محدد، معناها دفعة تجديد اشتراك عميل نهائي من بوابة العميل",
    )
    amount = models.DecimalField("المبلغ (جنيه)", max_digits=10, decimal_places=2)
    provider = models.CharField("بوابة الدفع", max_length=20, default="paymob")
    provider_order_id = models.CharField("رقم الطلب لدى البوابة", max_length=100, blank=True)
    status = models.CharField("الحالة", max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "معاملة دفع"
        verbose_name_plural = "معاملات الدفع"

    def __str__(self):
        return f"{self.company} — {self.amount} ج — {self.get_status_display()}"
