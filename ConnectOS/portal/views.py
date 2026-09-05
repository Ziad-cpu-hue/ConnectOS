from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from payments.models import PaymentTransaction
from payments.services import PaymobNotConfigured, PaymobService
from radius_core.models import RadAcct
from subscribers.models import Subscriber
from vouchers.models import TopupCard

from .decorators import subscriber_login_required


def portal_login(request):
    if request.session.get("portal_subscriber_id"):
        return redirect("portal:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        # اليوزرنيم هنا زي ما بيدخل بيه العميل على الهوت سبوت نفسه (بدون بادئة الشركة)
        sub = Subscriber.objects.filter(username=username, password=password).first()
        if sub:
            request.session["portal_subscriber_id"] = sub.id
            return redirect("portal:dashboard")
        messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")

    return render(request, "portal/login.html")


def portal_logout(request):
    request.session.flush()
    return redirect("portal:login")


@subscriber_login_required
def portal_dashboard(request):
    sub = request.subscriber
    usage = RadAcct.objects.filter(username=sub.username).order_by("-acctstarttime")[:10]
    total_mb = sum(s.total_mb for s in RadAcct.objects.filter(username=sub.username))
    return render(request, "portal/dashboard.html", {
        "sub": sub, "usage": usage, "total_mb": round(total_mb, 1),
    })


@subscriber_login_required
def portal_renew(request):
    sub = request.subscriber
    if not sub.can_self_renew:
        messages.error(request, "التجديد الذاتي غير مفعّل على حسابك، تواصل مع مزوّد الخدمة.")
        return redirect("portal:dashboard")
    if request.method == "POST":
        transaction = PaymentTransaction.objects.create(
            company=sub.company, subscriber=sub, amount=sub.plan.price,
        )
        try:
            service = PaymobService()
            iframe_url = service.create_payment_iframe_url(transaction)
            return redirect(iframe_url)
        except PaymobNotConfigured:
            messages.error(request, "الدفع الإلكتروني غير مفعّل حاليًا من مزود الخدمة، تواصل مع الدعم لتجديد اشتراكك يدويًا.")
            transaction.status = "failed"
            transaction.save(update_fields=["status"])
        except Exception as e:
            messages.error(request, f"تعذّر بدء عملية الدفع: {e}")
            transaction.status = "failed"
            transaction.save(update_fields=["status"])
    return redirect("portal:dashboard")


@subscriber_login_required
def portal_redeem_topup(request):
    """المشترك بيدخل كود كارت شحن رصيد من أي مكان (مش مربوط بسيرفر معين)
    فيتضاف المبلغ لرصيده مباشرة — بالظبط زي "كروت من أي مكان" عند Smart Radius."""
    sub = request.subscriber
    if not sub.can_self_topup:
        messages.error(request, "شحن الرصيد الذاتي غير مفعّل على حسابك، تواصل مع مزوّد الخدمة.")
        return redirect("portal:dashboard")
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        card = TopupCard.objects.filter(code=code).first()
        if not card:
            messages.error(request, "كود الكارت غير صحيح.")
        else:
            try:
                card.redeem(sub)
                messages.success(request, f"تم شحن رصيدك بمبلغ {card.amount} ج بنجاح.")
            except ValueError as e:
                messages.error(request, str(e))
    return redirect("portal:dashboard")
