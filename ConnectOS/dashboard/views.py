from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import company_required, platform_admin_required
from core.models import Company
from debts.models import Reseller
from nas_manager.models import NASServer
from plans.models import Plan
from radius_core.models import RadAcct
from subscribers.models import Subscriber
from vouchers.models import TopupBatch, Voucher, VoucherBatch


@login_required
def home(request):
    company = request.user.company

    total_devices = NASServer.objects.filter(company=company).count()
    online_devices = NASServer.objects.filter(company=company, is_online=True).count()
    active_vouchers = Voucher.objects.filter(batch__company=company, status="active").count()
    unused_vouchers = Voucher.objects.filter(batch__company=company, status="unused").count()

    total_subscribers = Subscriber.objects.filter(company=company).count()
    active_subscribers = sum(
        1 for s in Subscriber.objects.filter(company=company) if s.effective_status == "active"
    )
    online_now = RadAcct.objects.filter(company=company, acctstoptime__isnull=True).count()

    resellers = Reseller.objects.filter(company=company)
    total_debt = sum(r.current_debt for r in resellers)
    over_limit = sum(1 for r in resellers if r.is_over_limit)

    revenue = Voucher.objects.filter(
        batch__company=company, status__in=["active", "expired"]
    ).aggregate(total=Sum("plan__price"))["total"] or 0

    context = {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "active_vouchers": active_vouchers,
        "unused_vouchers": unused_vouchers,
        "total_subscribers": total_subscribers,
        "active_subscribers": active_subscribers,
        "online_now": online_now,
        "total_debt": total_debt,
        "over_limit": over_limit,
        "revenue": revenue,
        "plans_count": Plan.objects.filter(company=company).count(),
    }
    return render(request, "dashboard/home.html", context)


@platform_admin_required
def platform_overview(request):
    """شاشة خاصة بمالك منصة ConnectOS نفسه: كل الشركات المشتركة في المنصة.
    محمية بديكوريتور platform_admin_required على مستوى الـ view نفسه (مش بس القالب)،
    عشان أي مستخدم يحاول يدخل الرابط مباشرة ياخد 403 بدل ما يشوف بيانات كل الشركات."""
    companies = Company.objects.all().prefetch_related("payments", "users")
    total_revenue = sum(c.payments.aggregate(s=Sum("amount"))["s"] or 0 for c in companies)
    from core.models import PlatformPayment
    pending_payments = PlatformPayment.objects.filter(is_confirmed=False).select_related("company").order_by("paid_at")
    return render(request, "dashboard/platform_overview.html", {
        "companies": companies,
        "total_revenue": total_revenue,
        "pending_payments": pending_payments,
    })


@platform_admin_required
def confirm_payment(request, payment_id):
    """تأكيد وصول تحويل المحفظة الإلكترونية لفاتورة اشتراك شركة معينة، وتفعيل حسابها."""
    from django.shortcuts import get_object_or_404, redirect
    from django.utils import timezone
    from core.models import PlatformPayment
    payment = get_object_or_404(PlatformPayment, pk=payment_id)
    if request.method == "POST":
        payment.is_confirmed = True
        payment.confirmed_at = timezone.now()
        payment.save(update_fields=["is_confirmed", "confirmed_at"])
        payment.company.is_active = True
        payment.company.activated_at = timezone.now()
        payment.company.save(update_fields=["is_active", "activated_at"])
    return redirect("dashboard:platform_overview")


@platform_admin_required
def company_limits(request, company_id):
    """يسمح لمدير المنصة بس بإلغاء كل حدود باقة شركة معينة (unlimited_usage)،
    أو بتحديد حدود مخصصة (أعلى أو أقل) بدل حدود باقتها الافتراضية.
    ده منفصل تمامًا عن أي إعداد بيشوفه صاحب الشركة نفسه — مفيش أي زرار عندهم
    يقدروا بيه يغيروا الحدود دي؛ التحكم من هنا بس."""
    from django.contrib import messages as dj_messages
    from django.utils import timezone
    from core.limits import cards_printed_this_month
    from nas_manager.models import NASServer
    from subscribers.models import Subscriber

    company = get_object_or_404(Company, pk=company_id)

    if request.method == "POST":
        was_active = company.is_active
        company.is_active = request.POST.get("is_active") == "on"
        if company.is_active and not was_active:
            company.activated_at = timezone.now()
        elif not company.is_active:
            company.activated_at = None

        company.unlimited_usage = request.POST.get("unlimited_usage") == "on"

        def _parse_override(field_name):
            raw = (request.POST.get(field_name) or "").strip()
            if raw == "":
                return None
            try:
                value = int(raw)
                return value if value >= 0 else None
            except (TypeError, ValueError):
                return None

        company.override_max_clients = _parse_override("override_max_clients")
        company.override_max_servers = _parse_override("override_max_servers")
        company.override_max_print_cards = _parse_override("override_max_print_cards")
        company.save(update_fields=[
            "is_active", "activated_at", "unlimited_usage",
            "override_max_clients", "override_max_servers", "override_max_print_cards",
        ])
        dj_messages.success(request, f'تم تحديث حالة وحدود شركة "{company.name}".')
        return redirect("dashboard:company_limits", company_id=company.id)

    usage = {
        "clients": Subscriber.objects.filter(company=company).count(),
        "servers": NASServer.objects.filter(company=company).count(),
        "print_cards": cards_printed_this_month(company),
    }
    return render(request, "dashboard/company_limits.html", {"company": company, "usage": usage})


# ============================= الحسابات الفرعية =============================

@login_required
@company_required
def team(request):
    """إدارة فريق العمل: كل الحسابات الفرعية التابعة للشركة، وأكواد
    الانضمام المفتوحة، وزرار لتوليد كود جديد."""
    from django.contrib import messages
    from core.models import SubAccountInvite, User
    company = request.user.company

    if request.method == "POST" and request.POST.get("action") == "create_invite":
        role = request.POST.get("role", "support")
        if role not in dict(SubAccountInvite.ROLE_CHOICES):
            role = "support"
        SubAccountInvite.objects.create(
            company=company, role=role, created_by=request.user,
            code=SubAccountInvite.generate_code(),
        )
        messages.success(request, "تم توليد كود انضمام جديد — ابعته للموظف.")
        return redirect("dashboard:team")

    members = User.objects.filter(company=company).order_by("-date_joined")
    invites = SubAccountInvite.objects.filter(company=company).order_by("-created_at")
    return render(request, "dashboard/team.html", {
        "members": members, "invites": invites, "role_choices": SubAccountInvite.ROLE_CHOICES,
    })


@login_required
@company_required
def revoke_invite(request, invite_id):
    from django.contrib import messages
    from core.models import SubAccountInvite
    invite = get_object_or_404(SubAccountInvite, pk=invite_id, company=request.user.company)
    if request.method == "POST":
        invite.is_active = False
        invite.save(update_fields=["is_active"])
        messages.success(request, "تم إلغاء كود الانضمام.")
    return redirect("dashboard:team")


# ================================ سلة المهملات ================================

TRASH_REGISTRY = {
    "subscribers": {"model": Subscriber, "label": "المشتركون", "display": lambda o: f"{o.full_name} ({o.username})"},
    "servers": {"model": NASServer, "label": "السيرفرات", "display": lambda o: o.name},
    "resellers": {"model": Reseller, "label": "الموزعون", "display": lambda o: o.name},
    "voucher_batches": {"model": VoucherBatch, "label": "دفعات كروت الهوت سبوت", "display": lambda o: str(o)},
    "topup_batches": {"model": TopupBatch, "label": "دفعات كروت الشحن", "display": lambda o: str(o)},
}


@login_required
@company_required
def trash(request):
    """سلة المهملات — كل حاجة اتحذفت (Soft Delete) من أي قسم، مع إمكانية
    الاسترجاع أو الحذف النهائي الحقيقي من هنا بس."""
    company = request.user.company
    sections = []
    for key, cfg in TRASH_REGISTRY.items():
        items = cfg["model"].all_objects.filter(company=company, is_deleted=True).order_by("-deleted_at")
        sections.append({
            "key": key, "label": cfg["label"],
            "items": [{"pk": o.pk, "text": cfg["display"](o), "deleted_at": o.deleted_at} for o in items],
        })
    return render(request, "dashboard/trash.html", {"sections": sections})


@login_required
@company_required
def trash_restore(request, section, pk):
    from django.contrib import messages
    cfg = TRASH_REGISTRY.get(section)
    if not cfg:
        raise Http404
    obj = get_object_or_404(cfg["model"].all_objects, pk=pk, company=request.user.company, is_deleted=True)
    if request.method == "POST":
        obj.restore()
        messages.success(request, "تم الاسترجاع من سلة المهملات.")
    return redirect("dashboard:trash")


@login_required
@company_required
def trash_delete_forever(request, section, pk):
    from django.contrib import messages
    cfg = TRASH_REGISTRY.get(section)
    if not cfg:
        raise Http404
    obj = get_object_or_404(cfg["model"].all_objects, pk=pk, company=request.user.company, is_deleted=True)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "تم الحذف النهائي — الخطوة دي مش قابلة للتراجع.")
    return redirect("dashboard:trash")


# ================================== الإعدادات ==================================

@login_required
@company_required
def settings_view(request):
    from django.contrib import messages
    from core.models import get_or_create_company_settings
    company = request.user.company
    company_settings = get_or_create_company_settings(company)

    if request.method == "POST":
        company_settings.auto_suspend_enabled = request.POST.get("auto_suspend_enabled") == "on"
        company_settings.auto_suspend_time = request.POST.get("auto_suspend_time") or company_settings.auto_suspend_time
        company_settings.auto_delete_expired_enabled = request.POST.get("auto_delete_expired_enabled") == "on"
        try:
            company_settings.auto_delete_grace_days = int(request.POST.get("auto_delete_grace_days", 7))
        except (TypeError, ValueError):
            pass
        company_settings.single_server_login_enabled = request.POST.get("single_server_login_enabled") == "on"
        company_settings.auto_search_enabled = request.POST.get("auto_search_enabled") == "on"
        company_settings.save()
        messages.success(request, "تم حفظ الإعدادات.")
        return redirect("dashboard:settings")

    return render(request, "dashboard/settings.html", {"s": company_settings})


# ================================ الاحصائيات ================================

@login_required
@company_required
def statistics_view(request):
    """إحصائيات شاملة عن المشتركين وحركة مبيعات الكروت.
    ملحوظة معمارية مهمة: النظام هنا مركزي (RADIUS واحد لكل السيرفرات)،
    فالمشترك أو الكارت مش مقفول على سيرفر واحد بعينه زي بعض الأنظمة التقليدية
    — فالإحصائيات هنا على مستوى الشركة ككل، وهو أدق انعكاس لطريقة عمل النظام
    الفعلية بدل تقسيم وهمي حسب سيرفر."""
    from django.utils import timezone
    company = request.user.company
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    in_3_days = now + timezone.timedelta(days=3)

    subs = Subscriber.objects.filter(company=company)
    sub_stats = {
        "total": subs.count(),
        "active": sum(1 for s in subs if s.effective_status == "active"),
        "suspended": subs.filter(status="suspended").count(),
        "new_today": subs.filter(created_at__gte=today_start).count(),
        "expired": sum(1 for s in subs if s.effective_status == "expired"),
        "expiring_today": subs.filter(expires_at__date=now.date(), status="active").count(),
        "expiring_in_3_days": subs.filter(
            expires_at__gt=now, expires_at__lte=in_3_days, status="active"
        ).count(),
    }

    # تقرير مبيعات الكروت — فلترة بالفترة الزمنية والباقة
    date_from = request.GET.get("from", "")
    date_to = request.GET.get("to", "")
    plan_id = request.GET.get("plan", "")

    batches = VoucherBatch.objects.filter(company=company).select_related("plan")
    if date_from:
        batches = batches.filter(created_at__date__gte=date_from)
    if date_to:
        batches = batches.filter(created_at__date__lte=date_to)
    if plan_id:
        batches = batches.filter(plan_id=plan_id)

    sales_rows = [
        {"batch": b, "revenue": b.quantity * b.plan.price}
        for b in batches.order_by("-created_at")
    ]
    total_revenue = sum(r["revenue"] for r in sales_rows)

    return render(request, "dashboard/statistics.html", {
        "sub_stats": sub_stats,
        "sales_rows": sales_rows,
        "total_revenue": total_revenue,
        "plans": Plan.objects.filter(company=company),
        "date_from": date_from, "date_to": date_to, "plan_id": plan_id,
    })


# ================================= الاستهلاك =================================

@login_required
@company_required
def consumption_view(request):
    """استهلاك الباندويدث لكل سيرفر (جهاز ميكروتيك) على حدة — بيقرا مباشرة
    من جلسات radacct الحقيقية، مش أرقام تقديرية."""
    company = request.user.company
    servers = NASServer.objects.filter(company=company)

    rows = []
    for nas in servers:
        sessions = RadAcct.objects.filter(company=company, nasipaddress=nas.ip_address)
        total_in = sessions.aggregate(s=Sum("acctinputoctets"))["s"] or 0
        total_out = sessions.aggregate(s=Sum("acctoutputoctets"))["s"] or 0
        rows.append({
            "nas": nas,
            "sessions_count": sessions.count(),
            "total_mb": round((total_in + total_out) / (1024 * 1024), 1),
        })
    rows.sort(key=lambda r: r["total_mb"], reverse=True)
    return render(request, "dashboard/consumption.html", {"rows": rows})


# ================================ الملف الشخصى ================================

@login_required
def profile_view(request):
    """بيانات حساب المدير نفسه: اسم المستخدم، الاسم الكامل، رقم الهاتف،
    وتغيير كلمة المرور."""
    from django.contrib import messages
    from django.contrib.auth import update_session_auth_hash
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    user = request.user
    if request.method == "POST":
        user.first_name = request.POST.get("full_name", user.first_name)
        user.phone = request.POST.get("phone", user.phone)
        new_password = request.POST.get("new_password", "").strip()
        if new_password:
            try:
                validate_password(new_password, user=user)
                user.set_password(new_password)
            except ValidationError as e:
                for err in e.messages:
                    messages.error(request, err)
                return render(request, "dashboard/profile.html", {"u": user})
        user.save()
        if new_password:
            update_session_auth_hash(request, user)
        messages.success(request, "تم تحديث بياناتك.")
        return redirect("dashboard:profile")

    return render(request, "dashboard/profile.html", {"u": user})
