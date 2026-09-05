import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import RadAcct
from .services import AccountingError, handle_accounting_event


@csrf_exempt
@require_POST
def accounting_webhook(request):
    """نقطة النهاية اللي FreeRADIUS (عن طريق rlm_rest) أو أي وسيط بيبعتلها
    أحداث الـ Accounting الحية. محمية بالتحقق من (nas_ip + secret) مش بتوكن
    عام، لأن ده نفس منطق RADIUS الأصلي (Shared Secret لكل NAS)."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "JSON غير صالح."}, status=400)

    try:
        session = handle_accounting_event(payload)
    except AccountingError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=403)

    return JsonResponse({"ok": True, "session_id": session.id, "online": session.is_online})


@login_required
def online_now(request):
    """شاشة "المتصلين الآن" — بتقرا من radacct مباشرة (جلسات لسه ماخلصتش)."""
    company = request.user.company
    sessions = (
        RadAcct.objects.filter(company=company, acctstoptime__isnull=True)
        .order_by("-acctstarttime")
    )
    return render(request, "radius_core/online_now.html", {"sessions": sessions})
