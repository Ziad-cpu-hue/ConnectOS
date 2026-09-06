import random

from django.db import models
from django.utils import timezone

from core.models import Company, SoftDeleteModel
from plans.models import Plan


def generate_unique_code(length=10):
    """يولّد كود عشوائي فريد بطول محدد (أرقام فقط، زي الكروت الحقيقية)."""
    while True:
        code = "".join(str(random.randint(0, 9)) for _ in range(length))
        if not Voucher.objects.filter(code=code).exists():
            return code


class VoucherTemplate(models.Model):
    """قالب تصميم الكارت المطلوب طباعته (لميزة "صمّم شكل كارتك").
    layout_json بيخزن مواضع العناصر الحرة (سيريال/باسورد/سعر/QR) بالظبط
    زي مصمم Smart Radius (سحب وإفلات)، بدل التصميم الثابت القديم."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="voucher_templates", verbose_name="الشركة")
    name = models.CharField("اسم القالب", max_length=120)
    primary_color = models.CharField("اللون الأساسي", max_length=7, default="#1BA89B")
    secondary_color = models.CharField("اللون الثانوي", max_length=7, default="#E7A83D")
    logo_text = models.CharField("نص الشعار على الكارت", max_length=40, default="ConnectOS")
    support_phone = models.CharField("رقم الدعم الفني الظاهر على الكارت", max_length=20, blank=True)
    background_image = models.ImageField("صورة خلفية مخصصة (اختياري)", upload_to="voucher_backgrounds/", null=True, blank=True)
    show_qr = models.BooleanField("إظهار QR Code", default=True)
    layout_json = models.TextField(
        "مواضع العناصر (JSON)", blank=True,
        help_text="بيتحدد تلقائيًا من مصمم السحب والإفلات — متعدلوش يدوي",
    )
    is_default = models.BooleanField("القالب الافتراضي", default=False)

    class Meta:
        verbose_name = "قالب كارت"
        verbose_name_plural = "قوالب الكروت"

    def __str__(self):
        return self.name

    def get_layout(self):
        import json
        default_layout = {
            "code": {"x": 20, "y": 90, "font_size": 18, "color": "#1A1410"},
            "price": {"x": 20, "y": 30, "font_size": 14, "color": "#1A1410"},
            "logo": {"x": 20, "y": 15, "font_size": 13, "color": "#1BA89B"},
            "qr": {"x": 230, "y": 20, "size": 70},
        }
        if not self.layout_json:
            return default_layout
        try:
            return {**default_layout, **json.loads(self.layout_json)}
        except (ValueError, TypeError):
            return default_layout


class VoucherBatch(SoftDeleteModel):
    """دفعة طباعة كروت (كل دفعة مرتبطة بباقة واحدة وقالب واحد)"""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="voucher_batches", verbose_name="الشركة")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="batches", verbose_name="الباقة")
    template = models.ForeignKey(VoucherTemplate, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="القالب")
    quantity = models.PositiveIntegerField("عدد الكروت")
    created_by = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True, verbose_name="أنشأها")
    created_at = models.DateTimeField("تاريخ التوليد", auto_now_add=True)

    class Meta:
        verbose_name = "دفعة كروت"
        verbose_name_plural = "دفعات الكروت"
        ordering = ["-created_at"]

    def __str__(self):
        return f"دفعة {self.id} - {self.plan.name} ({self.quantity} كارت)"

    def generate_vouchers(self):
        """يولّد العدد المطلوب من الكروت الفريدة لهذه الدفعة، ويسجّلها فورًا
        فى radcheck عشان تبقى شغالة فعليًا على أي جهاز ميكروتيك من ثانية توليدها."""
        vouchers = [
            Voucher(code=generate_unique_code(), batch=self, plan=self.plan)
            for _ in range(self.quantity)
        ]
        Voucher.objects.bulk_create(vouchers)
        from .radius_sync import bulk_sync_vouchers_to_radius
        bulk_sync_vouchers_to_radius(vouchers)
        return vouchers

    def soft_delete(self):
        """نقل الدفعة كاملة لسلة المهملات — بيوقف كل كروتها عن الاشتغال على
        RADIUS فورًا (بدون حذف بياناتها، تقدر تسترجعها من سلة المهملات)."""
        from .radius_sync import set_voucher_radius_blocked
        super().soft_delete()
        for v in self.vouchers.all():
            set_voucher_radius_blocked(v, blocked=True)

    def restore(self):
        from .radius_sync import set_voucher_radius_blocked
        super().restore()
        for v in self.vouchers.all():
            if v.status != "expired":
                set_voucher_radius_blocked(v, blocked=False)


class Voucher(models.Model):
    """كارت شحن واحد بكود فريد من 10 أرقام"""

    STATUS_CHOICES = [
        ("unused", "غير مستخدم"),
        ("active", "مفعّل"),
        ("expired", "منتهي الصلاحية"),
    ]

    code = models.CharField("كود الكارت", max_length=10, unique=True)
    batch = models.ForeignKey(VoucherBatch, on_delete=models.CASCADE, related_name="vouchers", verbose_name="الدفعة")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="vouchers", verbose_name="الباقة")
    status = models.CharField("الحالة", max_length=10, choices=STATUS_CHOICES, default="unused")
    mac_address = models.CharField("عنوان الجهاز (MAC)", max_length=17, blank=True, null=True)
    activated_at = models.DateTimeField("تاريخ التفعيل", null=True, blank=True)
    expires_at = models.DateTimeField("تاريخ الانتهاء", null=True, blank=True)

    class Meta:
        verbose_name = "كارت"
        verbose_name_plural = "الكروت"
        ordering = ["-id"]

    def __str__(self):
        return self.code

    def activate(self):
        self.status = "active"
        self.activated_at = timezone.now()
        self.expires_at = self.activated_at + timezone.timedelta(days=self.plan.duration_days)
        self.save()
        from .radius_sync import sync_voucher_to_radius
        sync_voucher_to_radius(self)

    def mark_expired(self):
        self.status = "expired"
        self.save(update_fields=["status"])
        from .radius_sync import sync_voucher_to_radius
        sync_voucher_to_radius(self)


def generate_unique_topup_code(length=12):
    """كود كارت شحن رصيد — منفصل تمامًا عن أكواد كروت الهوت سبوت، وشغال من
    أي سيرفر لأنه مش مربوط بباقة أو دفعة كروت هوت سبوت أصلًا (زي "كروت من
    أي مكان" عند Smart Radius)."""
    while True:
        code = "".join(str(random.randint(0, 9)) for _ in range(length))
        if not TopupCard.objects.filter(code=code).exists():
            return code


class TopupBatch(SoftDeleteModel):
    """دفعة كروت شحن رصيد — كل كارت فيها بقيمة مالية ثابتة، وبيتشحن على أي
    مشترك بغض النظر عن أي سيرفر هو متصل بيه."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="topup_batches", verbose_name="الشركة")
    amount = models.DecimalField("قيمة كل كارت (جنيه)", max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField("عدد الكروت")
    created_by = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True, verbose_name="أنشأها")
    created_at = models.DateTimeField("تاريخ التوليد", auto_now_add=True)

    class Meta:
        verbose_name = "دفعة كروت شحن رصيد"
        verbose_name_plural = "دفعات كروت شحن الرصيد"
        ordering = ["-created_at"]

    def __str__(self):
        return f"دفعة شحن {self.id} - {self.amount} ج × {self.quantity}"

    def generate_cards(self):
        cards = [
            TopupCard(code=generate_unique_topup_code(), batch=self, company=self.company, amount=self.amount)
            for _ in range(self.quantity)
        ]
        TopupCard.objects.bulk_create(cards)
        return cards


class TopupCard(models.Model):
    """كارت شحن رصيد واحد — بيستخدمه المشترك من بوابة الخدمة الذاتية
    (portal) بغض النظر عن أي سيرفر هو عليه، فيتضاف المبلغ لرصيده مباشرة."""

    STATUS_CHOICES = [
        ("unused", "غير مستخدم"),
        ("used", "تم استخدامه"),
    ]

    code = models.CharField("كود الكارت", max_length=12, unique=True)
    batch = models.ForeignKey(TopupBatch, on_delete=models.CASCADE, related_name="cards", verbose_name="الدفعة")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="topup_cards", verbose_name="الشركة")
    amount = models.DecimalField("القيمة (جنيه)", max_digits=10, decimal_places=2)
    status = models.CharField("الحالة", max_length=10, choices=STATUS_CHOICES, default="unused")
    used_by = models.ForeignKey(
        "subscribers.Subscriber", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="topup_redemptions", verbose_name="استخدمه المشترك",
    )
    used_at = models.DateTimeField("تاريخ الاستخدام", null=True, blank=True)

    class Meta:
        verbose_name = "كارت شحن رصيد"
        verbose_name_plural = "كروت شحن الرصيد"
        ordering = ["-id"]

    def __str__(self):
        return self.code

    def redeem(self, subscriber):
        """يشحن رصيد المشترك بقيمة الكارت — بيتحقق إن الكارت من نفس شركة
        المشترك ولسه مش مستخدم قبل ما يسمح بأي حاجة."""
        if self.status != "unused":
            raise ValueError("الكارت ده اتستخدم قبل كده.")
        if self.company_id != subscriber.company_id:
            raise ValueError("الكارت ده مش تابع لنفس الشبكة.")
        subscriber.balance = subscriber.balance + self.amount
        subscriber.save(update_fields=["balance"])
        self.status = "used"
        self.used_by = subscriber
        self.used_at = timezone.now()
        self.save(update_fields=["status", "used_by", "used_at"])
        return subscriber
