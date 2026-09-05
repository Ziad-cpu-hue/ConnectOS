"""
منطق استقبال أحداث الـ RADIUS Accounting (بداية/تحديث/نهاية جلسة).
في العالم الحقيقي: FreeRADIUS بيستقبل أحداث Accounting من الميكروتيك على
بورت 1813 (UDP)، ولو ضفنا rlm_rest module في ملف الإعدادات بتاعه، هو نفسه
هيبعت POST بالبيانات دي لنقطة النهاية اللي عملناها في views.py — بالشكل ده
مش محتاجين نعمل عميل RADIUS كامل بايثون، واحنا بنستفيد من FreeRADIUS نفسه
كـ "مُترجم" للبروتوكول، وبس نستقبل النتيجة كـ JSON عادي.
"""
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from nas_manager.models import NASServer
from .models import RadAcct


class AccountingError(Exception):
    pass


def authenticate_nas(nas_ip, secret):
    """يتأكد إن الطلب جاي فعلاً من جهاز NAS معروف وبمفتاحه السري الصحيح."""
    try:
        nas = NASServer.objects.get(ip_address=nas_ip, secret=secret)
    except NASServer.DoesNotExist:
        raise AccountingError("جهاز غير معروف أو المفتاح السري غلط.")
    return nas


def _activate_voucher_on_first_use(username):
    """لو اليوزرنيم ده كارت هوت سبوت لسه "غير مستخدم"، أول Accounting Start
    حقيقي بتاعه هو اللي بيشغّل عداد الصلاحية (activate) — بالظبط زي سلوك
    الكروت الحقيقي فى الواقع (الكارت بيبدأ يعدّ من أول دخول مش من التوليد)."""
    from vouchers.models import Voucher
    voucher = Voucher.objects.filter(code=username, status="unused").first()
    if voucher:
        voucher.activate()


def handle_accounting_event(payload):
    """
    payload المتوقع (نفس أسماء صفات RADIUS القياسية):
    {
      "nas_ip": "172.29.38.140",
      "nas_secret": "xxxx",
      "acct_status_type": "Start" | "Interim-Update" | "Stop",
      "acct_session_id": "...",
      "acct_unique_id": "...",
      "username": "...",
      "framed_ip": "10.5.50.12",
      "calling_station_id": "AA:BB:CC:DD:EE:FF",
      "input_octets": 123456,
      "output_octets": 654321,
      "terminate_cause": "User-Request"   # في حالة Stop بس
    }
    """
    nas = authenticate_nas(payload.get("nas_ip"), payload.get("nas_secret"))

    status = payload.get("acct_status_type")
    unique_id = payload.get("acct_unique_id")
    if not unique_id:
        raise AccountingError("acct_unique_id مطلوب.")

    now = timezone.now()
    # الجهاز بعت لينا أي حدث Accounting معناه إنه لسه حي ومتصل
    nas.is_online = True
    nas.last_seen = now
    nas.save(update_fields=["is_online", "last_seen"])

    username = payload.get("username", "")
    if status == "Start":
        _activate_voucher_on_first_use(username)

    session, created = RadAcct.objects.get_or_create(
        acctuniqueid=unique_id,
        defaults={
            "company": nas.company,
            "acctsessionid": payload.get("acct_session_id", unique_id),
            "username": payload.get("username", ""),
            "nasipaddress": nas.ip_address,
            "nasportid": payload.get("nas_port_id", ""),
            "framedipaddress": payload.get("framed_ip") or None,
            "callingstationid": payload.get("calling_station_id", ""),
            "acctstarttime": now,
        },
    )

    if status == "Interim-Update":
        session.acctupdatetime = now
        session.acctinputoctets = payload.get("input_octets", session.acctinputoctets)
        session.acctoutputoctets = payload.get("output_octets", session.acctoutputoctets)
        session.save()
    elif status == "Stop":
        session.acctstoptime = now
        session.acctinputoctets = payload.get("input_octets", session.acctinputoctets)
        session.acctoutputoctets = payload.get("output_octets", session.acctoutputoctets)
        session.acctterminatecause = payload.get("terminate_cause", "")
        session.save()

    return session
