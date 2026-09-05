"""
منطق التحقق من حدود باقة المنصة (PlatformPlan) لكل شركة (تاجر شبكة/عميل المنصة).

كل باقة منصة (اللي بتتعرض في صفحة الهبوط) بتحدد سقف استخدام: أقصى عدد
مشتركين، أقصى عدد سيرفرات، وأقصى عدد كروت طباعة (فاوتشرات) شهريًا. الدوال
هنا بترجع None لو العملية مسموحة، أو نص رسالة تحذير جاهزة للعرض للمستخدم
لو هتتجاوز الحد.

ملحوظة: مدير المنصة يقدر يلغي كل الحدود لشركة معينة (unlimited_usage) أو
يحط حدود مخصصة (override_*) بتحل محل حدود الباقة الافتراضية — شوف
Company.effective_max_clients / effective_max_servers / effective_max_print_cards
في core/models.py.

الاستيرادات هنا "كسولة" (جوه كل دالة) لتفادي أي استيراد دائري بين core
والتطبيقات التانية (subscribers, nas_manager, vouchers).
"""
from django.db.models import Sum
from django.utils import timezone


def check_subscriber_limit(company, adding=1):
    """يتحقق قبل إضافة مشترك/مشتركين جدد. adding = العدد المطلوب إضافته دلوقتي."""
    limit = company.effective_max_clients
    if limit is None:
        return None
    from subscribers.models import Subscriber
    current = Subscriber.objects.filter(company=company).count()
    if current + adding > limit:
        return (
            f"وصلت للحد الأقصى المسموح به من المشتركين في باقتك الحالية "
            f"({limit} مشترك، وعندك دلوقتي {current}). احذف مشترك مش محتاجه، "
            f"أو رقّي باقتك، أو تواصل مع الدعم الفني لزيادة الحد."
        )
    return None


def check_server_limit(company, adding=1):
    """يتحقق قبل إضافة جهاز/سيرفر جديد. adding = العدد المطلوب إضافته دلوقتي."""
    limit = company.effective_max_servers
    if limit is None:
        return None
    from nas_manager.models import NASServer
    current = NASServer.objects.filter(company=company).count()
    if current + adding > limit:
        return (
            f"وصلت للحد الأقصى المسموح به من أجهزة السيرفرات في باقتك الحالية "
            f"({limit} سيرفر، وعندك دلوقتي {current}). احذف جهاز مش شغال، "
            f"أو رقّي باقتك، أو تواصل مع الدعم الفني لزيادة الحد."
        )
    return None


def cards_printed_this_month(company):
    """إجمالي عدد كروت الفاوتشرات (الهوت سبوت) اللي اتولّدت للشركة من أول الشهر الحالي."""
    from vouchers.models import VoucherBatch
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return VoucherBatch.objects.filter(
        company=company, created_at__gte=month_start,
    ).aggregate(total=Sum("quantity"))["total"] or 0


def check_print_cards_limit(company, adding):
    """يتحقق قبل توليد دفعة كروت جديدة. adding = عدد الكروت المطلوب توليدها في الدفعة دي."""
    limit = company.effective_max_print_cards
    if limit is None:
        return None
    used = cards_printed_this_month(company)
    if used + adding > limit:
        remaining = max(limit - used, 0)
        return (
            f"باقتك الحالية بتسمح بطباعة {limit} كارت شهريًا بس، وطبعت "
            f"{used} كارت لحد دلوقتي الشهر ده — يعني باقيلك {remaining} كارت "
            f"مش أكتر. قلّل عدد الكروت المطلوبة في الدفعة، أو استنى الشهر الجاي، "
            f"أو تواصل مع الدعم الفني لترقية باقتك."
        )
    return None
