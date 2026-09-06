from django.db import models

from core.models import Company


class Plan(models.Model):
    """باقة اشتراك (تُستخدم كأساس لتوليد الكروت)

    ملحوظة مهمة: حجب المواقع الإباحية بقى إعداد أساسي على مستوى المنصة
    كلها (مش خيار اختياري لكل باقة) — بيتفرض على كل جهاز ميكروتيك تلقائيًا
    من سكريبت التركيب نفسه (شوف nas_manager/content_filter.py)
    ومفيش أي زرار أو حقل في الداشبورد بيقدر يلغيه. اتشال الحقل القديم
    block_adult_sites من هنا عمدًا عشان محدش يفتكر إنه اختياري.
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="plans", verbose_name="الشركة")
    name = models.CharField("اسم الباقة", max_length=120)
    quota_mb = models.PositiveIntegerField("الكوطة بالميجابايت", null=True, blank=True,
                                            help_text="اتركه فارغًا لباقة غير محدودة الكمية")
    duration_days = models.PositiveIntegerField("مدة الصلاحية (أيام)")
    speed_limit_kbps = models.PositiveIntegerField("حد السرعة (كيلوبت/ث)", null=True, blank=True)
    price = models.DecimalField("السعر (جنيه)", max_digits=8, decimal_places=2)
    speed_equation_enabled = models.BooleanField("تفعيل معادلة السرعة (توزيع عادل وقت الزحمة)", default=False)
    allow_open_speed = models.BooleanField("السماح بالعمل بالسرعة المفتوحة (بدون حد أقصى)", default=False)
    is_active = models.BooleanField("مفعّلة", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "باقة"
        verbose_name_plural = "الباقات"
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} - {self.price} ج"
