"""
جداول متوافقة 100% مع سكيمة FreeRADIUS القياسية (raddb/mods-config/sql/main/*/schema.sql).
الفكرة: لو حطيت FreeRADIUS حقيقي وضبطت rlm_sql بتاعه يقرا من نفس قاعدة
البيانات دي (نفس أسماء الجداول والأعمدة بالظبط)، هيشتغل فورًا من غير أي
تعديل في FreeRADIUS نفسه — القاعدة دي بقت "مصدر الحقيقة" لبيانات الاشتراكات.

المشتركين (Subscriber) في تطبيق subscribers هم اللي بيتصرفوا كـ "واجهة
بيزنس" فوق الجداول دي، وبيعملوا sync تلقائي عليها (شوف subscribers/signals.py).
"""
from django.db import models

from core.models import Company


class RadCheck(models.Model):
    """بيانات التحقق من الدخول (يوزر/باسورد) — يقابل جدول radcheck في FreeRADIUS."""

    username = models.CharField(max_length=64, db_index=True)
    attribute = models.CharField(max_length=64, default="Cleartext-Password")
    op = models.CharField(max_length=2, default=":=")
    value = models.CharField(max_length=253)

    class Meta:
        db_table = "radcheck"
        verbose_name = "RadCheck (بيانات دخول RADIUS)"
        verbose_name_plural = "RadCheck (بيانات دخول RADIUS)"
        indexes = [models.Index(fields=["username"])]

    def __str__(self):
        return f"{self.username} / {self.attribute}"


class RadReply(models.Model):
    """صلاحيات الرد بعد نجاح الدخول (سرعة، مدة الجلسة...) — يقابل جدول radreply."""

    username = models.CharField(max_length=64, db_index=True)
    attribute = models.CharField(max_length=64)
    op = models.CharField(max_length=2, default=":=")
    value = models.CharField(max_length=253)

    class Meta:
        db_table = "radreply"
        verbose_name = "RadReply (صلاحيات الجلسة)"
        verbose_name_plural = "RadReply (صلاحيات الجلسة)"
        indexes = [models.Index(fields=["username"])]

    def __str__(self):
        return f"{self.username} / {self.attribute}={self.value}"


class RadNas(models.Model):
    """أجهزة الـ NAS (الميكروتيك) المسموح لها تسأل السيرفر — يقابل جدول nas.
    NASServer في تطبيق nas_manager هو الواجهة البيزنس، وبيعمل sync هنا تلقائي."""

    nasname = models.CharField(max_length=128, unique=True, help_text="عنوان IP بتاع الجهاز")
    shortname = models.CharField(max_length=32)
    type = models.CharField(max_length=30, default="mikrotik")
    secret = models.CharField(max_length=60)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "nas"
        verbose_name = "RadNas (جهاز NAS)"
        verbose_name_plural = "RadNas (أجهزة NAS)"

    def __str__(self):
        return f"{self.shortname} ({self.nasname})"


class RadAcct(models.Model):
    """جلسات الاستخدام الفعلية (Accounting) — يقابل جدول radacct.
    بتتغذى من نقطة نهاية /radius/accounting/ اللي FreeRADIUS (عن طريق
    rlm_rest أو سكريبت وسيط) بيبعتلها أحداث Start / Interim-Update / Stop."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="sessions", null=True, blank=True)
    acctsessionid = models.CharField(max_length=64, db_index=True)
    acctuniqueid = models.CharField(max_length=32, unique=True)
    username = models.CharField(max_length=64, db_index=True)
    nasipaddress = models.GenericIPAddressField()
    nasportid = models.CharField(max_length=32, blank=True)
    framedipaddress = models.GenericIPAddressField(null=True, blank=True)
    callingstationid = models.CharField("MAC العميل", max_length=50, blank=True)
    acctstarttime = models.DateTimeField(null=True, blank=True)
    acctupdatetime = models.DateTimeField(null=True, blank=True)
    acctstoptime = models.DateTimeField(null=True, blank=True)
    acctinputoctets = models.BigIntegerField("بايت مرفوعة", default=0)
    acctoutputoctets = models.BigIntegerField("بايت منزّلة", default=0)
    acctterminatecause = models.CharField(max_length=32, blank=True)

    class Meta:
        db_table = "radacct"
        verbose_name = "RadAcct (جلسة استخدام)"
        verbose_name_plural = "RadAcct (جلسات الاستخدام)"
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["acctstoptime"]),
        ]

    def __str__(self):
        return f"{self.username} @ {self.nasipaddress}"

    @property
    def is_online(self):
        return self.acctstoptime is None

    @property
    def total_mb(self):
        return round((self.acctinputoctets + self.acctoutputoctets) / (1024 * 1024), 1)
