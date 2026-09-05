from django.contrib.auth.models import AbstractUser
from django.db import models


class PlatformPlan(models.Model):
    """باقة اشتراك في منصة ConnectOS نفسها (مش باقات التاجر لعملائه).
    دي اللي بتتعرض في قسم "الباقات" على صفحة الهبوط، وبتحدد سقف الاستخدام
    المسموح للشركة (تاجر الشبكة) على المنصة: عدد المشتركين، السيرفرات،
    وكروت الطباعة."""

    name = models.CharField("اسم الباقة", max_length=100)
    max_clients = models.PositiveIntegerField("أقصى عدد مشتركين")
    max_servers = models.PositiveIntegerField("أقصى عدد سيرفرات")
    max_print_cards = models.PositiveIntegerField("أقصى عدد كروت طباعة")
    price_monthly = models.DecimalField("السعر الشهري (جنيه)", max_digits=8, decimal_places=2)
    is_featured = models.BooleanField("الأكثر طلبًا", default=False)
    order = models.PositiveIntegerField("الترتيب في العرض", default=0)
    is_active = models.BooleanField("متاحة للاشتراك", default=True)

    class Meta:
        verbose_name = "باقة اشتراك المنصة"
        verbose_name_plural = "باقات اشتراك المنصة"
        ordering = ["order", "price_monthly"]

    def __str__(self):
        return f"{self.name} — {self.price_monthly} ج/شهريًا"


class Company(models.Model):
    """صاحب الشبكة (المستأجر - Tenant) المشترك في منصة ConnectOS"""

    PLAN_CHOICES = [
        ("starter", "البداية"),
        ("growth", "النمو"),
        ("pro", "الاحتراف"),
    ]

    name = models.CharField("اسم الشبكة", max_length=200)
    owner_phone = models.CharField("رقم تواصل المالك", max_length=20, blank=True)
    subscription_plan = models.CharField(
        "خطة الاشتراك في المنصة (قديم)", max_length=20, choices=PLAN_CHOICES, default="starter",
        help_text="حقل قديم قبل باقات PlatformPlan — لسه موجود لتوافق البيانات القديمة",
    )
    platform_plan = models.ForeignKey(
        PlatformPlan, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="companies", verbose_name="باقة المنصة",
    )
    is_active = models.BooleanField(
        "نشط", default=True,
        help_text="لو متوقف، الشركة تقدر تفتح لوحة التحكم وتتصفحها عادي، لكن مايقدروش "
                   "يستخدموا أي ميزة فعلية (إضافة جهاز/مشترك/كروت...إلخ) لحد ما يتفعّل الحساب.",
    )
    activated_at = models.DateTimeField(
        "تاريخ آخر تفعيل", null=True, blank=True,
        help_text="بيتحدّث تلقائيًا لحظة التفعيل — بيتحكم في ظهور شريط \"تم التفعيل\" لفترة قصيرة بعدها.",
    )
    monthly_fee = models.DecimalField("قيمة الاشتراك الشهري", max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField("تاريخ الانضمام", auto_now_add=True)

    # ---- تحكّم مدير المنصة في حدود الاستخدام لكل شركة على حدة ----
    unlimited_usage = models.BooleanField(
        "بدون أي حدود استخدام", default=False,
        help_text="لو مفعّل، الشركة دي مش هتتقيد بأي حد من حدود باقتها (عدد مشتركين/"
                   "سيرفرات/كروت طباعة شهريًا) مهما كانت باقتها — بيتحكم فيه مدير "
                   "المنصة بس من شاشة \"عملاء المنصة\".",
    )
    override_max_clients = models.PositiveIntegerField(
        "حد مخصص لعدد المشتركين", null=True, blank=True,
        help_text="سيبها فاضية عشان تستخدم حد الباقة المشترك فيها. لو حطيت رقم هنا، هو اللي هيتطبق بدل حد الباقة.",
    )
    override_max_servers = models.PositiveIntegerField(
        "حد مخصص لعدد السيرفرات", null=True, blank=True,
        help_text="سيبها فاضية عشان تستخدم حد الباقة المشترك فيها. لو حطيت رقم هنا، هو اللي هيتطبق بدل حد الباقة.",
    )
    override_max_print_cards = models.PositiveIntegerField(
        "حد مخصص لعدد كروت الطباعة شهريًا", null=True, blank=True,
        help_text="سيبها فاضية عشان تستخدم حد الباقة المشترك فيها. لو حطيت رقم هنا، هو اللي هيتطبق بدل حد الباقة.",
    )

    class Meta:
        verbose_name = "شركة"
        verbose_name_plural = "الشركات"

    def __str__(self):
        return self.name

    # الحدود الفعلية اللي المفروض تتطبق فعليًا على الشركة دي — بتاخد في اعتبارها
    # الأولوية: unlimited_usage (بدون حدود خالص) > حد مخصص من مدير المنصة > حد الباقة العادي.
    # None معناها "بدون حد أقصى".
    @property
    def effective_max_clients(self):
        if self.unlimited_usage:
            return None
        if self.override_max_clients is not None:
            return self.override_max_clients
        return self.platform_plan.max_clients if self.platform_plan_id else None

    @property
    def effective_max_servers(self):
        if self.unlimited_usage:
            return None
        if self.override_max_servers is not None:
            return self.override_max_servers
        return self.platform_plan.max_servers if self.platform_plan_id else None

    @property
    def effective_max_print_cards(self):
        if self.unlimited_usage:
            return None
        if self.override_max_print_cards is not None:
            return self.override_max_print_cards
        return self.platform_plan.max_print_cards if self.platform_plan_id else None


class PlatformPayment(models.Model):
    """سجل مدفوعات الشركة لاشتراكها في منصة ConnectOS نفسها (وليس اشتراكات عملاء الشبكة)"""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="payments", verbose_name="الشركة")
    amount = models.DecimalField("المبلغ", max_digits=8, decimal_places=2)
    method = models.CharField("طريقة الدفع", max_length=50, default="تحويل بنكي")
    is_confirmed = models.BooleanField(
        "تم تأكيد الدفع", default=False,
        help_text="بيتفعّل يدويًا من مدير المنصة بعد ما يتأكد من وصول المبلغ للمحفظة",
    )
    confirmed_at = models.DateTimeField("تاريخ التأكيد", null=True, blank=True)
    paid_at = models.DateTimeField("تاريخ الدفع", auto_now_add=True)

    class Meta:
        verbose_name = "دفعة اشتراك المنصة"
        verbose_name_plural = "مدفوعات اشتراك المنصة"
        ordering = ["-paid_at"]

    def __str__(self):
        return f"{self.company.name} - {self.amount} ج"


class User(AbstractUser):
    """مستخدم النظام: صاحب شبكة، مدير، أو موظف دعم فني"""

    ROLE_CHOICES = [
        ("owner", "مالك الشركة"),
        ("admin", "مدير"),
        ("support", "دعم فني"),
        ("platform_admin", "مدير المنصة"),
    ]

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="users",
        verbose_name="الشركة", null=True, blank=True,
    )
    role = models.CharField("الصلاحية", max_length=20, choices=ROLE_CHOICES, default="owner")
    phone = models.CharField("رقم الهاتف", max_length=20, blank=True)
    last_login_ip = models.GenericIPAddressField("آخر IP دخول", null=True, blank=True)

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"

    def save(self, *args, **kwargs):
        """أي حساب "سوبريوزر" (Django superuser) — يعني أي حساب اتعمل بأمر
        createsuperuser من التيرمنال/PowerShell — بيبقى تلقائيًا "مدير المنصة"
        (platform_admin)، من غير ما حد يحتاج يدخل يعدّل الصلاحية يدويًا من
        /admin/. كده أي يوزر/باسورد بتعملهم بـ createsuperuser بيشتغلوا فورًا
        كحساب مالك المنصة، وحساب العميل العادي (اللي بيتعمل من صفحة الاشتراك
        في الموقع نفسه) فضل زي ما هو owner عادي مربوط بشركته."""
        if self.is_superuser:
            self.role = "platform_admin"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username


class AuditLog(models.Model):
    """سجل تدقيق لعمليات الأدمن الحساسة (حذف، إيقاف، تعديل صلاحيات...).
    أساس بسيط قابل للتوسعة — مش شامل كل عملية في النظام، لكنه مطبّق على
    أهم العمليات الحساسة فعليًا (حذف مشترك/جهاز، تسوية دين)."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_actions")
    action = models.CharField("الإجراء", max_length=100)
    details = models.CharField("تفاصيل", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "سجل تدقيق"
        verbose_name_plural = "سجل التدقيق"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.action} — {self.created_at:%Y-%m-%d %H:%M}"


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """المدير الافتراضي: بيستبعد أي حاجة في سلة المهملات تلقائيًا من كل
    الاستعلامات العادية (قوائم، فلاتر...) من غير ما نلمس أي كود موجود."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """Mixin لأي موديل عايزين نديله "سلة مهملات" بدل الحذف النهائي المباشر:
    حذف = is_deleted=True (بيختفي من كل القوائم فورًا)، واسترجاع = رجّعها تاني.
    الحذف النهائي الحقيقي بيحصل بس من داخل شاشة سلة المهملات نفسها."""

    is_deleted = models.BooleanField("في سلة المهملات", default=False)
    deleted_at = models.DateTimeField("تاريخ النقل لسلة المهملات", null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # يشمل المحذوف — يُستخدم في شاشة سلة المهملات بس

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class SubAccountInvite(models.Model):
    """كود انضمام لحساب فرعي (موظف) تحت شركة معينة — نفس فكرة "كود الانضمام"
    عند Smart Radius: صاحب الشبكة بيولّد كود، وبيديه لموظفه، وهو بيسجّل بيه
    نفسه على /join/<code>/ من غير ما صاحب الشبكة يكتب له يوزر/باسورد يدوي."""

    ROLE_CHOICES = [
        ("admin", "مدير"),
        ("support", "دعم فني"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="invites", verbose_name="الشركة")
    code = models.CharField("كود الانضمام", max_length=12, unique=True)
    role = models.CharField("الصلاحية الممنوحة", max_length=20, choices=ROLE_CHOICES, default="support")
    created_by = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="أنشأه")
    is_active = models.BooleanField("فعّال", default=True)
    used_by = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="استخدمه")
    used_at = models.DateTimeField("تاريخ الاستخدام", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "كود انضمام حساب فرعي"
        verbose_name_plural = "أكواد انضمام الحسابات الفرعية"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} ({self.company.name})"

    @staticmethod
    def generate_code():
        import random
        import string
        while True:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not SubAccountInvite.objects.filter(code=code).exists():
                return code

    @property
    def is_usable(self):
        return self.is_active and self.used_by_id is None


class CompanySettings(models.Model):
    """إعدادات قابلة للتحكم لكل شركة — نفس فكرة صفحة "الإعدادات" عند
    Smart Radius (إيقاف المشتركين تلقائي، حذف المنتهيين، الدخول من أي
    سيرفر، البحث التلقائي...). بيتقرأ من هنا في أي مهمة مجدولة (cron)."""

    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="settings")

    auto_suspend_enabled = models.BooleanField("إيقاف المشتركين المنتهيين تلقائيًا", default=True)
    auto_suspend_time = models.TimeField("موعد الإيقاف اليومي", default="00:00")

    auto_delete_expired_enabled = models.BooleanField("نقل المشتركين المنتهيين لسلة المهملات تلقائيًا", default=False)
    auto_delete_grace_days = models.PositiveIntegerField("بعد كام يوم من الانتهاء", default=7)

    single_server_login_enabled = models.BooleanField(
        "السماح للمشترك بالدخول من أي سيرفر", default=True,
        help_text="لو متوقف، هيتقفل المشترك على السيرفر اللي دخل بيه أول مرة بس",
    )
    auto_search_enabled = models.BooleanField("تفعيل البحث التلقائي عند الكتابة", default=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "إعدادات الشركة"
        verbose_name_plural = "إعدادات الشركات"

    def __str__(self):
        return f"إعدادات {self.company.name}"


def get_or_create_company_settings(company):
    settings_obj, _ = CompanySettings.objects.get_or_create(company=company)
    return settings_obj
