import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import PaymentTransaction
from .services import PaymobNotConfigured, PaymobService


@login_required
def checkout(request):
    company = request.user.company
    if request.method == "POST":
        try:
            amount = float(request.POST.get("amount", 0))
        except ValueError:
            amount = 0
        if amount <= 0:
            messages.error(request, "أدخل مبلغ صحيح.")
            return redirect("payments:checkout")

        transaction = PaymentTransaction.objects.create(company=company, amount=amount)
        try:
            service = PaymobService()
            iframe_url = service.create_payment_iframe_url(transaction)
            return redirect(iframe_url)
        except PaymobNotConfigured:
            messages.error(
                request,
                "بوابة الدفع غير مفعّلة بعد على المنصة (مفاتيح Paymob غير مضبوطة). "
                "تواصل مع الدعم الفني لتفعيل الدفع الإلكتروني."
            )
            transaction.status = "failed"
            transaction.save(update_fields=["status"])
        except Exception as e:
            messages.error(request, f"تعذّر بدء عملية الدفع: {e}")
            transaction.status = "failed"
            transaction.save(update_fields=["status"])
        return redirect("payments:checkout")

    transactions = PaymentTransaction.objects.filter(company=company)[:20]
    return render(request, "payments/checkout.html", {"transactions": transactions})


@csrf_exempt
def paymob_webhook(request):
    """Paymob بيبعت هنا نتيجة كل عملية دفع (نجحت أو فشلت) مع توقيع HMAC."""
    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False}, status=400)

    obj = payload.get("obj", payload)
    received_hmac = request.GET.get("hmac", "")

    try:
        service = PaymobService()
    except Exception:
        return JsonResponse({"ok": False, "error": "not configured"}, status=503)

    if not service.verify_webhook_hmac(obj, received_hmac):
        return JsonResponse({"ok": False, "error": "invalid signature"}, status=403)

    order_id = str(obj.get("order", {}).get("id", ""))
    success = obj.get("success", False)

    try:
        transaction = PaymentTransaction.objects.get(provider_order_id=order_id)
    except PaymentTransaction.DoesNotExist:
        return JsonResponse({"ok": False, "error": "transaction not found"}, status=404)

    transaction.status = "paid" if success else "failed"
    if success:
        transaction.paid_at = timezone.now()
        transaction.save()
        if transaction.subscriber_id:
            transaction.subscriber.renew()
    else:
        transaction.save()

    return JsonResponse({"ok": True})
