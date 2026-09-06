"""
Sync تلقائي بين Subscriber (الواجهة البيزنس) وجداول radcheck/radreply
(اللي FreeRADIUS الحقيقي بيقرا منها مباشرة). كل حفظ أو حذف لمشترك بينعكس
فورًا على الجداول دي، فمفيش حاجة اسمها "زرار مزامنة يدوي" — البيانات دايمًا
متسقة.
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from radius_core.models import RadCheck, RadReply
from radius_core.speed_policy import apply_plan_speed_policy

from .models import Subscriber


@receiver(post_save, sender=Subscriber)
def sync_subscriber_to_radius(sender, instance, **kwargs):
    uname = instance.username  # فريد عالميًا فعليًا، بيتحقق منه FreeRADIUS مباشرة

    RadCheck.objects.update_or_create(
        username=uname, attribute="Cleartext-Password",
        defaults={"op": ":=", "value": instance.password},
    )

    # لو موقوف أو منتهي، نضيف قيد Auth-Type := Reject عشان FreeRADIUS يرفضه فورًا
    if instance.effective_status != "active":
        RadCheck.objects.update_or_create(
            username=uname, attribute="Auth-Type",
            defaults={"op": ":=", "value": "Reject"},
        )
    else:
        RadCheck.objects.filter(username=uname, attribute="Auth-Type").delete()

    if instance.mac_lock:
        RadCheck.objects.update_or_create(
            username=uname, attribute="Calling-Station-Id",
            defaults={"op": "==", "value": instance.mac_lock},
        )
    else:
        RadCheck.objects.filter(username=uname, attribute="Calling-Station-Id").delete()

    # صلاحيات الرد: حد السرعة من الباقة. ثلاث حالات ممكنة حسب إعدادات
    # الباقة نفسها:
    #  - allow_open_speed=True  → مفيش أي حد سرعة خالص (سرعة مفتوحة فعليًا)
    #  - speed_equation_enabled=True → بيتحط في مجموعة "توزيع عادل" على
    #    الميكروتيك (Mikrotik-Group) بدل حد ثابت، عشان السرعة تتوزع
    #    ديناميكيًا حسب الزحمة (PCQ) بدل ما تكون سقف صلب لكل مشترك
    #  - غير كده → حد سرعة ثابت عادي (Mikrotik-Rate-Limit) زي ما كان
    apply_plan_speed_policy(uname, instance.plan)

    if instance.expires_at:
        RadCheck.objects.update_or_create(
            username=uname, attribute="Expiration",
            defaults={"op": ":=", "value": instance.expires_at.strftime("%d %b %Y %H:%M")},
        )
    else:
        RadCheck.objects.filter(username=uname, attribute="Expiration").delete()


@receiver(post_delete, sender=Subscriber)
def remove_subscriber_from_radius(sender, instance, **kwargs):
    uname = instance.username
    RadCheck.objects.filter(username=uname).delete()
    RadReply.objects.filter(username=uname).delete()
