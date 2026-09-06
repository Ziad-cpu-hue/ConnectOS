from django.db import models

from core.models import Company, SoftDeleteModel


class NASServer(SoftDeleteModel):
    """جهاز MikroTik واحد (نقطة وصول / عمود) مربوط بشبكة صاحب الحساب"""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="nas_servers", verbose_name="الشركة")
    name = models.CharField("اسم الجهاز", max_length=150, help_text="مثال: عمود شارع النصر")
    ip_address = models.GenericIPAddressField("عنوان IP")
    secret = models.CharField("المفتاح السري (RADIUS Secret)", max_length=150)
    api_username = models.CharField("يوزر RouterOS API", max_length=100, blank=True, default="admin")
    api_password = models.CharField("باسورد RouterOS API", max_length=150, blank=True)
    api_port = models.PositiveIntegerField("بورت RouterOS API", default=8728)
    region = models.CharField("المنطقة", max_length=150, blank=True)
    latitude = models.FloatField("خط العرض", null=True, blank=True)
    longitude = models.FloatField("خط الطول", null=True, blank=True)
    is_online = models.BooleanField("متصل الآن", default=False)
    last_seen = models.DateTimeField("آخر ظهور", null=True, blank=True)
    last_test_result = models.CharField("نتيجة آخر اختبار اتصال", max_length=255, blank=True)

    # فتح الأجهزة (VPN/NAT) — بيانات نفق SSTP اللي بيخلي أي جهاز خلف NAT
    # (زي أغلب أجهزة ميكروتك عند التجار) قابل للوصول من غير IP عام.
    # ملاحظة مهمة: الحقول دي طبقة البيانات والواجهة بس — التشغيل الفعلي
    # محتاج سيرفر VPN حقيقي شغال (SoftEther/OpenVPN) يستقبل الاتصال ده،
    # شوف ملف VPN_SETUP.md المرفق لخطوات تجهيزه.
    vpn_username = models.CharField("يوزر اتصال VPN", max_length=40, blank=True)
    vpn_password = models.CharField("باسورد اتصال VPN", max_length=40, blank=True)
    vpn_tunnel_port = models.PositiveIntegerField("بورت النفق المخصص", null=True, blank=True, unique=True)
    vpn_connected = models.BooleanField("النفق متصل الآن", default=False)
    vpn_last_handshake = models.DateTimeField("آخر اتصال VPN", null=True, blank=True)

    created_at = models.DateTimeField("تاريخ الإضافة", auto_now_add=True)

    class Meta:
        verbose_name = "جهاز ميكروتيك"
        verbose_name_plural = "أجهزة الميكروتيك"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.ip_address})"

    def ensure_vpn_credentials(self):
        """يولّد يوزر/باسورد/بورت نفق فريدين أول مرة بس (زي ما Smart Radius
        بيعمل تلقائيًا وقت "إضافة سيرفر جديد")."""
        import random
        import string
        changed = False
        if not self.vpn_username:
            self.vpn_username = "usr_" + "".join(random.choices(string.digits, k=8))
            changed = True
        if not self.vpn_password:
            self.vpn_password = "pass_" + "".join(random.choices(string.digits, k=6))
            changed = True
        if not self.vpn_tunnel_port:
            last = NASServer.all_objects.exclude(pk=self.pk).aggregate(
                m=models.Max("vpn_tunnel_port")
            )["m"]
            self.vpn_tunnel_port = (last or 8199) + 1
            changed = True
        if changed:
            self.save(update_fields=["vpn_username", "vpn_password", "vpn_tunnel_port"])
        return changed

    @property
    def vpn_direct_link(self):
        from django.conf import settings
        if not self.vpn_tunnel_port:
            return ""
        return f"{settings.VPN_PUBLIC_HOST}:{self.vpn_tunnel_port}"
