from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import NotificationLog, NotificationSettings
from .services import TelegramNotifier


@login_required
def settings_view(request):
    company = request.user.company
    settings_obj, _ = NotificationSettings.objects.get_or_create(company=company)

    if request.method == "POST":
        settings_obj.telegram_bot_token = request.POST.get("telegram_bot_token", "").strip()
        settings_obj.telegram_chat_id = request.POST.get("telegram_chat_id", "").strip()
        settings_obj.notify_low_balance = "notify_low_balance" in request.POST
        settings_obj.notify_new_debt = "notify_new_debt" in request.POST
        settings_obj.notify_subscriber_expiry = "notify_subscriber_expiry" in request.POST
        settings_obj.save()
        messages.success(request, "تم حفظ إعدادات التنبيهات.")
        return redirect("notifications:settings")

    logs = NotificationLog.objects.filter(company=company)[:20]
    return render(request, "notifications/settings.html", {"settings": settings_obj, "logs": logs})


@login_required
def send_test(request):
    company = request.user.company
    settings_obj, _ = NotificationSettings.objects.get_or_create(company=company)
    if request.method == "POST":
        ok, error = TelegramNotifier(settings_obj).send(
            f"🔔 رسالة تجربة من ConnectOS لشركة {company.name}. لو وصلتك الرسالة دي، التكامل شغال تمام!"
        )
        if ok:
            messages.success(request, "تم إرسال رسالة التجربة بنجاح — تشيّك على تيليجرام.")
        else:
            messages.error(request, f"فشل الإرسال: {error or 'تأكد من التوكن و chat_id.'}")
    return redirect("notifications:settings")
