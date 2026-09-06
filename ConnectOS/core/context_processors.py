"""
بيجهّز حالة تفعيل شركة المستخدم الحالي عشان شريط الحالة اللي بيظهر في أعلى
لوحة التحكم — بدل ما كل view يحتاج يبعتها يدوي في الـ context بتاعه.
"""
from django.utils import timezone

RECENTLY_ACTIVATED_WINDOW_SECONDS = 60 * 60 * 24  # يوم واحد بعد التفعيل يفضل الشريط الأخضر ظاهر


def company_status(request):
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return {}
    if not getattr(user, "company_id", None) or user.role == "platform_admin":
        return {}

    company = user.company
    if not company.is_active:
        return {"company_unpaid": True}

    if company.activated_at:
        seconds_since = (timezone.now() - company.activated_at).total_seconds()
        if seconds_since < RECENTLY_ACTIVATED_WINDOW_SECONDS:
            return {"company_just_activated": True}

    return {}
