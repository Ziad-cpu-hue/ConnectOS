"""
أمر يومي (يُشغَّل بـ cron) يفحص المشتركين اللي هينتهي اشتراكهم خلال يوم،
ويبعت تنبيه تيليجرام لصاحب الشركة لو مفعّل عنده الخيار ده في الإعدادات.
مثال cron (كل يوم الساعة 9 صباحًا):
    0 9 * * * cd /path/to/project && python manage.py notify_expiring_subscribers
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import NotificationSettings
from notifications.services import TelegramNotifier
from subscribers.models import Subscriber


class Command(BaseCommand):
    help = "يبعت تنبيه تيليجرام لأصحاب الشبكات عن مشتركين هينتهي اشتراكهم خلال يوم"

    def handle(self, *args, **options):
        now = timezone.now()
        soon = now + timezone.timedelta(days=1)

        expiring = Subscriber.objects.filter(
            status="active", expires_at__gte=now, expires_at__lte=soon,
        ).select_related("company", "plan")

        sent, skipped = 0, 0
        for company_id in expiring.values_list("company_id", flat=True).distinct():
            company_subs = expiring.filter(company_id=company_id)
            settings_obj = NotificationSettings.objects.filter(
                company_id=company_id, notify_subscriber_expiry=True
            ).first()
            if not settings_obj or not settings_obj.is_configured:
                skipped += company_subs.count()
                continue

            names = "، ".join(s.full_name for s in company_subs[:10])
            message = (
                f"⏰ تنبيه: {company_subs.count()} مشترك هينتهي اشتراكهم خلال 24 ساعة:\n{names}"
            )
            ok, _ = TelegramNotifier(settings_obj).send(message)
            if ok:
                sent += 1

        self.stdout.write(self.style.SUCCESS(f"تم إرسال {sent} تنبيه، وتخطي {skipped} مشترك (تنبيهات غير مفعّلة)."))
