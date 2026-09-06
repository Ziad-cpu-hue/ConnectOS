"""
ترجمة إعدادات سرعة الباقة (Plan) لصلاحيات RADIUS reply فعلية، مستخدمة من
subscribers/signals.py (للمشتركين الدائمين) و vouchers/radius_sync.py
(لكروت الهوت سبوت) عشان المنطق يكون واحد موحّد في مكان واحد بس.

ثلاث حالات:
1) allow_open_speed=True   → مفيش أي Mikrotik-Rate-Limit خالص (سرعة مفتوحة
   فعليًا من غير أي سقف، وده اللي بيخلّي RouterOS ميحطش أي حد على الجلسة).
2) speed_equation_enabled=True → بدل ما نحط سقف صلب واحد، نضيف
   Mikrotik-Group=connectos-fair-share عشان الجهاز يحط المشترك في مجموعة
   المستخدمين اللي معرّفة على الراوتر بطابور PCQ (توزيع عادل ديناميكي
   للسرعة المتاحة وقت الزحمة بين كل المشتركين المتصلين في نفس المجموعة،
   بدل سقف ثابت مهما كانت الزحمة). سكريبت التركيب (nas_manager) هو اللي
   بيعرّف المجموعة والطابور دول فعليًا على الجهاز.
3) غير كده → سقف سرعة ثابت عادي (Mikrotik-Rate-Limit) زي ما كان أصلًا.
"""
from radius_core.models import RadCheck, RadReply

FAIR_SHARE_GROUP = "connectos-fair-share"


def apply_plan_speed_policy(username, plan):
    """يحدّث radreply attributes الخاصة بالسرعة لليوزرنيم ده حسب إعدادات الباقة."""
    # نمسح الحالة القديمة الأول عشان منسيبش قيم متضاربة من تبديل الإعداد
    RadReply.objects.filter(username=username, attribute="Mikrotik-Rate-Limit").delete()
    RadReply.objects.filter(username=username, attribute="Mikrotik-Group").delete()

    if plan.allow_open_speed:
        # سرعة مفتوحة فعليًا: مفيش أي reply خاص بالسرعة، يعني الراوتر
        # هيدي المشترك أقصى سرعة متاحة على خط الإنترنت نفسه من غير أي تقييد.
        return

    if plan.speed_equation_enabled:
        RadReply.objects.update_or_create(
            username=username, attribute="Mikrotik-Group",
            defaults={"op": ":=", "value": FAIR_SHARE_GROUP},
        )
        return

    if plan.speed_limit_kbps:
        rate = f"{plan.speed_limit_kbps}k/{plan.speed_limit_kbps}k"
        RadReply.objects.update_or_create(
            username=username, attribute="Mikrotik-Rate-Limit",
            defaults={"op": ":=", "value": rate},
        )
