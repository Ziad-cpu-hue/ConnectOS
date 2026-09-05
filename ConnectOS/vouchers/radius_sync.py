"""
مزامنة كروت الهوت سبوت مع جداول RADIUS الحقيقية — نفس المبدأ المطبّق على
Subscriber بالظبط. من غير الملف ده، الكروت كانت مجرد أرقام فى قاعدة
البيانات من غير أي قدرة فعلية على تسجيل الدخول على شبكة الواي فاي — وده
كان أخطر فجوة فى النظام لأن "كروت الهوت سبوت" هي الميزة الأساسية اللي
بيتباع على أساسها المنتج كله.

المنطق:
- الكارت بيتسجل فى radcheck من لحظة توليده (Cleartext-Password = نفس الكود)
  وده اللي يخليه شغال فورًا على أي جهاز ميكروتيك مربوط، حتى قبل أول استخدام.
- أول ما حد يدخل بيه فعليًا (أول Accounting Start حقيقي)، بنفعّل العداد
  (activate) ونحدد تاريخ الانتهاء، ونحطه فى radcheck (Expiration) عشان
  FreeRADIUS نفسه يرفضه تلقائيًا بعد ما ينتهي من غير أي كود إضافي.
"""
from radius_core.models import RadCheck, RadReply
from radius_core.speed_policy import FAIR_SHARE_GROUP, apply_plan_speed_policy


def sync_voucher_to_radius(voucher):
    uname = voucher.code
    RadCheck.objects.update_or_create(
        username=uname, attribute="Cleartext-Password",
        defaults={"op": ":=", "value": voucher.code},
    )
    # نفس منطق سياسة السرعة المطبّق على المشتركين الدائمين بالظبط (سرعة
    # مفتوحة / توزيع عادل PCQ / سقف ثابت) — شوف radius_core/speed_policy.py
    apply_plan_speed_policy(uname, voucher.plan)
    if voucher.mac_address:
        RadCheck.objects.update_or_create(
            username=uname, attribute="Calling-Station-Id",
            defaults={"op": "==", "value": voucher.mac_address},
        )
    if voucher.status == "expired":
        RadCheck.objects.update_or_create(
            username=uname, attribute="Auth-Type",
            defaults={"op": ":=", "value": "Reject"},
        )
    else:
        RadCheck.objects.filter(username=uname, attribute="Auth-Type").delete()

    if voucher.expires_at:
        RadCheck.objects.update_or_create(
            username=uname, attribute="Expiration",
            defaults={"op": ":=", "value": voucher.expires_at.strftime("%d %b %Y %H:%M")},
        )


def bulk_sync_vouchers_to_radius(vouchers):
    """يُستخدم بعد bulk_create مباشرة (Django signals مش بتتفعّل مع bulk_create)."""
    checks = [
        RadCheck(username=v.code, attribute="Cleartext-Password", op=":=", value=v.code)
        for v in vouchers
    ]
    RadCheck.objects.bulk_create(checks)

    replies = []
    for v in vouchers:
        plan = v.plan
        if plan.allow_open_speed:
            continue  # سرعة مفتوحة: مفيش أي reply خاص بالسرعة خالص
        if plan.speed_equation_enabled:
            replies.append(RadReply(username=v.code, attribute="Mikrotik-Group", op=":=", value=FAIR_SHARE_GROUP))
        elif plan.speed_limit_kbps:
            rate = f"{plan.speed_limit_kbps}k/{plan.speed_limit_kbps}k"
            replies.append(RadReply(username=v.code, attribute="Mikrotik-Rate-Limit", op=":=", value=rate))
    if replies:
        RadReply.objects.bulk_create(replies)


def remove_voucher_from_radius(voucher):
    RadCheck.objects.filter(username=voucher.code).delete()
    RadReply.objects.filter(username=voucher.code).delete()


def set_voucher_radius_blocked(voucher, blocked: bool):
    """يُستخدم وقت نقل دفعة كروت لسلة المهملات أو استرجاعها."""
    if blocked:
        RadCheck.objects.update_or_create(
            username=voucher.code, attribute="Auth-Type",
            defaults={"op": ":=", "value": "Reject"},
        )
    else:
        RadCheck.objects.filter(username=voucher.code, attribute="Auth-Type").delete()
