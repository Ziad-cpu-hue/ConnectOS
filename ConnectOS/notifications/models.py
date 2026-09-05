from django.db import models

from core.models import Company


class NotificationSettings(models.Model):
    """إعدادات تنبيهات تيليجرام لكل شركة (كل شركة ليها بوت/شات منفصل)."""

    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="notification_settings")
    telegram_bot_token = models.CharField("توكن بوت تيليجرام", max_length=100, blank=True)
    telegram_chat_id = models.CharField("Chat ID", max_length=50, blank=True)
    notify_low_balance = models.BooleanField("تنبيه عند اقتراب حد المديونية", default=True)
    notify_new_debt = models.BooleanField("تنبيه عند تسجيل دين جديد", default=True)
    notify_subscriber_expiry = models.BooleanField("تنبيه قبل انتهاء اشتراك عميل بيوم", default=False)

    class Meta:
        verbose_name = "إعدادات التنبيهات"
        verbose_name_plural = "إعدادات التنبيهات"

    @property
    def is_configured(self):
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    def __str__(self):
        return f"تنبيهات {self.company.name}"


class NotificationLog(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="notification_logs")
    message = models.TextField()
    success = models.BooleanField(default=False)
    error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company} — {self.created_at:%Y-%m-%d %H:%M}"
