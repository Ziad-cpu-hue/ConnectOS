from django.db import models
from django.utils import timezone

from core.models import Company, SoftDeleteModel
from plans.models import Plan


class SubscriberGroup(models.Model):
    """تقسيم المشتركين لمجموعات صغيرة (مثلاً حسب الشارع أو المدينة أو
    العمارة) لتسهيل الإدارة والمتابعة — نفس الميزة الموجودة عند Smart Radius."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="subscriber_groups", verbose_name="الشركة")
    name = models.CharField("اسم المجموعة", max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مجموعة مشتركين"
        verbose_name_plural = "مجموعات المشتركين"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Subscriber(SoftDeleteModel):
    """مشترك على الهوت سبوت (يوزر/باسورد دائم، مختلف عن كارت الشحن اللي
    بيتباع مرة واحدة). ده المفهوم اللي كان ناقص بالكامل في المشروع الأصلي —
    Smart Radius بيسميه "المشتركين" في القائمة الجانبية.

    عند الحفظ، بيعمل sync تلقائي لجدول radcheck/radreply (شوف signals.py)
    عشان FreeRADIUS الحقيقي يقدر يتحقق من بياناته فورًا بدون أي كود وسيط."""

    STATUS_CHOICES = [
        ("active", "نشط"),
        ("suspended", "موقوف"),
        ("expired", "منتهي"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="subscribers", verbose_name="الشركة")
    full_name = models.CharField("الاسم بالكامل", max_length=150)
    phone = models.CharField("رقم الهاتف", max_length=20, blank=True)
    username = models.CharField("اسم المستخدم", max_length=64, unique=True,
                                 help_text="فريد على مستوى المنصة كلها (لأن العميل بيكتبه في صفحة الهوت سبوت مباشرة)")
    password = models.CharField("كلمة المرور", max_length=64)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscribers", verbose_name="الباقة")
    group = models.ForeignKey(SubscriberGroup, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="subscribers", verbose_name="المجموعة")
    can_self_renew = models.BooleanField("يقدر يجدد اشتراكه بنفسه من البوابة", default=True)
    can_self_topup = models.BooleanField("يقدر يشحن رصيده بنفسه من البوابة", default=True)
    mac_lock = models.CharField("قفل بجهاز معين (MAC)", max_length=17, blank=True,
                                 help_text="اتركه فارغًا للسماح بالدخول من أي جهاز")
    status = models.CharField("الحالة", max_length=12, choices=STATUS_CHOICES, default="active")
    expires_at = models.DateTimeField("تاريخ انتهاء الاشتراك", null=True, blank=True)
    balance = models.DecimalField("الرصيد (من كروت الشحن)", max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مشترك"
        verbose_name_plural = "المشتركون"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.username})"

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at < timezone.now())

    @property
    def effective_status(self):
        if self.is_deleted or self.status == "suspended":
            return "suspended"
        if self.is_expired:
            return "expired"
        return "active"

    def renew(self):
        """تجديد الاشتراك بنفس مدة الباقة الحالية من اليوم."""
        base = timezone.now()
        self.expires_at = base + timezone.timedelta(days=self.plan.duration_days)
        self.status = "active"
        self.save()
