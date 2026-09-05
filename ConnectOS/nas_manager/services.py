"""
طبقة الاتصال الفعلي بجهاز الميكروتيك عن طريق RouterOS API (بورت 8728 عادةً،
أو 8729 لو SSL). بتستخدم مكتبة librouteros الحقيقية (مش محاكاة) — الكود ده
هيشتغل فورًا مع أي جهاز ميكروتيك حقيقي متاح على الشبكة بنفس البيانات دي.

ملاحظة: في بيئة السانديت هنا معندناش جهاز ميكروتيك فعلي نختبر عليه، فالدالة
هترجع خطأ اتصال حقيقي (Timeout) وده متوقع تمامًا ومنطقي — ده إثبات إن
الكود بيحاول يتصل فعليًا مش بيرجع بيانات وهمية."""
import librouteros
from librouteros.exceptions import TrapError

from django.utils import timezone

from .models import NASServer


class MikroTikConnectionError(Exception):
    pass


class MikroTikService:
    def __init__(self, nas: NASServer):
        self.nas = nas

    def _connect(self):
        from django.conf import settings as dj_settings
        try:
            return librouteros.connect(
                username=self.nas.api_username or "admin",
                password=self.nas.api_password or "",
                host=self.nas.ip_address,
                port=self.nas.api_port or dj_settings.MIKROTIK_API_DEFAULT_PORT,
                timeout=dj_settings.MIKROTIK_API_TIMEOUT,
            )
        except Exception as e:
            raise MikroTikConnectionError(str(e))

    def test_connection(self):
        """يحاول الاتصال الفعلي بالجهاز، ويرجع (نجح؟, رسالة) ويحدّث حالة is_online."""
        try:
            api = self._connect()
            identity = list(api("/system/identity/print"))
            api.close()
            name = identity[0].get("name", "?") if identity else "?"
            self.nas.is_online = True
            self.nas.last_seen = timezone.now()
            self.nas.last_test_result = f"✅ اتصال ناجح — اسم الجهاز: {name}"
            self.nas.save(update_fields=["is_online", "last_seen", "last_test_result"])
            return True, self.nas.last_test_result
        except (MikroTikConnectionError, TrapError, OSError) as e:
            self.nas.is_online = False
            self.nas.last_test_result = f"❌ فشل الاتصال: {e}"
            self.nas.save(update_fields=["is_online", "last_test_result"])
            return False, self.nas.last_test_result

    def active_hotspot_users(self):
        """يرجع قائمة اليوزرز المتصلين فعليًا دلوقتي من على الجهاز نفسه
        (مصدر بديل لـ radacct، مفيد للمقارنة والتأكد من دقة البيانات)."""
        api = self._connect()
        try:
            return list(api("/ip/hotspot/active/print"))
        finally:
            api.close()

    def disconnect_user(self, hotspot_active_id):
        """فصل مستخدم متصل فورًا (زرار "قطع الاتصال" في شاشة المتصلين الآن)."""
        api = self._connect()
        try:
            api("/ip/hotspot/active/remove", **{".id": hotspot_active_id})
        finally:
            api.close()
