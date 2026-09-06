"""
تكامل حقيقي وشغّال مع Telegram Bot API (مش محاكاة). كل اللي محتاجه المستخدم
هو ينشئ بوت من @BotFather ويحط الـ token + chat_id في شاشة الإعدادات،
والرسائل هتتبعت فورًا لأن Telegram API مفتوح وبسيط (POST عادي، من غير أي
اعتماد على مزود دفع أو مفاتيح معقدة زي بوابات الدفع المصرية)."""
import requests

from .models import NotificationLog

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    def __init__(self, settings_obj):
        self.settings = settings_obj

    def send(self, message):
        if not self.settings.is_configured:
            NotificationLog.objects.create(
                company=self.settings.company, message=message,
                success=False, error="التوكن أو chat_id غير مضبوطين.",
            )
            return False, "التوكن أو chat_id غير مضبوطين."

        url = TELEGRAM_API.format(token=self.settings.telegram_bot_token)
        try:
            resp = requests.post(
                url,
                json={"chat_id": self.settings.telegram_chat_id, "text": message, "parse_mode": "HTML"},
                timeout=8,
            )
            ok = resp.status_code == 200 and resp.json().get("ok", False)
            error = "" if ok else resp.text[:250]
        except requests.RequestException as e:
            ok, error = False, str(e)[:250]

        NotificationLog.objects.create(company=self.settings.company, message=message, success=ok, error=error)
        return ok, error


def notify_company(company, message):
    """دالة مختصرة تُستخدم من أي تطبيق تاني (debts, subscribers...) لبعت تنبيه."""
    settings_obj, _ = NotificationSettingsModel().get_or_create_for(company)
    return TelegramNotifier(settings_obj).send(message)


class NotificationSettingsModel:
    def get_or_create_for(self, company):
        from .models import NotificationSettings
        return NotificationSettings.objects.get_or_create(company=company)
