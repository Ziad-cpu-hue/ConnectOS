"""
Middleware يمنع أي "فعل حقيقي" (POST — إضافة جهاز، مشترك، توليد كروت، أي
حاجة بتغيّر بيانات) من أي شركة لسه مدير المنصة ما أكدلهاش استلام الدفع
(Company.is_active = False).

صاحب الشركة يقدر يسجّل دخول ويفتح لوحة التحكم ويتصفحها عادي (أي طلب GET
بيشتغل زي ما هو، عشان يقدر يشوف الشاشات وشريط "لسه مش مفعّل")، لكن أي
طلب POST (يعني أي عملية فعلية) هيترفض برسالة واضحة لحد ما يتفعّل حسابه.

مدير المنصة (platform_admin) مش متأثر بالقيد ده أبدًا مهما كانت شركته،
وصفحة تسجيل الخروج مستثناة عشان محدش يتقفل جوه حسابه من غير ما يقدر يخرج.
"""
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


class CompanyActivationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._exempt_paths = None

    def _get_exempt_paths(self):
        if self._exempt_paths is None:
            try:
                self._exempt_paths = {reverse("core:logout")}
            except Exception:
                self._exempt_paths = set()
        return self._exempt_paths

    def __call__(self, request):
        if self._should_block(request):
            messages.error(
                request,
                "حسابك لسه مش مفعّل. لازم إدارة المنصة تأكد استلام الدفع الأول "
                "قبل ما تقدر تستخدم أي ميزة في النظام (إضافة جهاز، مشترك، كروت، "
                "أو أي حاجة تانية) — تقدر تتصفح لوحة التحكم عادي لحد ما يتفعّل حسابك.",
            )
            referer = request.META.get("HTTP_REFERER")
            return redirect(referer or "dashboard:home")
        return self.get_response(request)

    def _should_block(self, request):
        if request.method != "POST":
            return False
        if request.path in self._get_exempt_paths():
            return False
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        if user.role == "platform_admin":
            return False
        if not user.company_id:
            return False
        return not user.company.is_active
