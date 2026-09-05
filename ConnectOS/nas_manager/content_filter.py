"""
حجب المواقع الإباحية — إعداد أساسي إجباري على مستوى المنصة كلها.

مهم جدًا: الكود ده مش مربوط بأي حقل Boolean في أي موديل، ومش مربوط بأي
شرط request.POST.get(...) — ده عمدًا. الدالة هنا بترجع نفس السكريبت
دايمًا لأي جهاز، وبتتلزق تلقائيًا في build_setup_script() (nas_manager/views.py)
مع كل جهاز جديد من غير أي زرار "تفعيل/إيقاف" في أي شاشة. لو حد عايز
يشيل الحجب ده، الطريقة الوحيدة إنه يعدّل الكود نفسه ويعمل نشر جديد — مش
حاجة بتتغير من الداشبورد.

الطريقة الفنية (على RouterOS v7+):
1) /ip dns adlist: ميزة أصلية في RouterOS بتنزّل قائمة نطاقات وبتحجبها على
   مستوى الـ DNS resolver بتاع الراوتر نفسه (نفس فكرة "Ad-list" اللي
   Mikrotik أضافتها للحجب العام، وبنستخدمها هنا لحجب نطاقات إباحية بدل
   الإعلانات فقط).
2) تحويل إجباري (NAT redirect) لأي طلب DNS خارج الجهاز (بورت 53 UDP/TCP)
   لراوتر نفسه — عشان نمنع أي جهاز عميل من تخطي الفلتر بتغيير الـ DNS يدويًا
   لسيرفر خارجي (زي 8.8.8.8) من إعدادات شبكته.

ملحوظة أمانة: زي أي فلترة DNS في العالم، الطريقة دي مش 100% مثالية ضد كل
حالات التحايل (مثلاً تطبيق DNS-over-HTTPS مدمج جوه المتصفح بيتصل مباشرة
بسيرفر تشفير خارجي على بورت 443 مش 53، فمينفعش نعترضه بنفس الأسلوب). دي
نفس القيود التقنية الموجودة في أي حل فلترة DNS مبني على راوتر (وده تقريبًا
كل حلول الفلترة عند مزودي الإنترنت الصغار)، مش قصور في الكود نفسه.
"""
from django.conf import settings


def build_mandatory_content_filter_script():
    """يرجع فقرة RouterOS ثابتة — بتتلزق إجباريًا في كل سكريبت تركيب جهاز."""
    adlist_url = settings.CONTENT_FILTER_ADLIST_URL
    return f"""
# ===== ConnectOS: حجب إجباري للمحتوى الإباحي (إعداد أساسي غير قابل للإلغاء) =====
# ملحوظة: الفقرة دي بتتلزق تلقائيًا مع كل جهاز جديد، ومفيش أي إعداد في
# لوحة التحكم بيقدر يوقفها أو يستثني جهاز معين منها.
/ip dns
set allow-remote-requests=yes
/ip dns adlist
add url="{adlist_url}" comment="ConnectOS-mandatory-adult-content-filter"

/ip firewall nat
add chain=dstnat protocol=udp dst-port=53 action=redirect to-ports=53 comment="ConnectOS: إجبار كل الأجهزة على DNS الراوتر (منع تخطي فلتر المحتوى)"
add chain=dstnat protocol=tcp dst-port=53 action=redirect to-ports=53 comment="ConnectOS: نفس الإجبار على DNS عبر TCP"
:log info "ConnectOS: تم تفعيل الحجب الإجباري للمحتوى الإباحي على هذا الجهاز"
""".strip("\n")


def build_fair_share_queue_script():
    """
    يعرّف طابور PCQ ومجموعة مستخدمين "توزيع عادل وقت الزحمة" على الجهاز —
    أي مشترك على باقة مفعّل فيها speed_equation_enabled بيتحط في المجموعة
    دي تلقائيًا عن طريق صفة RADIUS الاسمها Mikrotik-Group (شوف
    radius_core/speed_policy.py)، فبدل سقف سرعة صلب ثابت، السرعة المتاحة
    بتتوزع ديناميكيًا وبعدل بين كل المشتركين المتصلين في المجموعة دي وقت
    الزحمة، وترجع أعلى لما الشبكة تفضى.
    """
    from radius_core.speed_policy import FAIR_SHARE_GROUP
    return f"""
# ===== ConnectOS: مجموعة "توزيع السرعة العادل وقت الزحمة" (PCQ) =====
/queue type
add name=connectos-pcq-down kind=pcq pcq-classifier=dst-address
add name=connectos-pcq-up kind=pcq pcq-classifier=src-address
/ip hotspot user profile
add name="{FAIR_SHARE_GROUP}" queue-type=connectos-pcq-up/connectos-pcq-down shared-users=1
:log info "ConnectOS: تم تجهيز مجموعة توزيع السرعة العادل ({FAIR_SHARE_GROUP})"
""".strip("\n")
