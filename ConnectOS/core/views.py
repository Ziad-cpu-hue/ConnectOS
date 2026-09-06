from django.contrib.auth import login
from django.shortcuts import get_object_or_404, redirect, render

from .forms import JoinSubAccountForm, SignupForm, SubscribeForm
from .models import PlatformPlan, SubAccountInvite


def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    platform_plans = PlatformPlan.objects.filter(is_active=True)
    return render(request, "core/landing.html", {"platform_plans": platform_plans})


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard:home")
    else:
        form = SignupForm(initial={"plan": request.GET.get("plan", "growth")})
    return render(request, "core/signup.html", {"form": form})


def subscribe(request, plan_id):
    """صفحة الاشتراك في باقة معينة من قسم "الباقات" في صفحة الهبوط.
    نفس فكرة register/<id> بتاعة Smart Radius — يملأ بياناته، وبعد الحفظ
    بيتحول لصفحة فاتورة فيها تفاصيل الدفع (تحويل على المحفظة الإلكترونية)."""
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    plan = get_object_or_404(PlatformPlan, pk=plan_id, is_active=True)
    if request.method == "POST":
        form = SubscribeForm(request.POST, plan=plan)
        if form.is_valid():
            user, invoice = form.save()
            login(request, user)
            return redirect("core:subscribe_invoice", invoice_id=invoice.id)
    else:
        form = SubscribeForm(plan=plan)
    return render(request, "core/subscribe.html", {"form": form, "plan": plan})


def subscribe_invoice(request, invoice_id):
    """شاشة الفاتورة بعد الاشتراك مباشرة — بتعرض المبلغ ورقم المحفظة الإلكترونية
    اللي هيحول عليها العميل، وحالة "بانتظار تأكيد الدفع" لحد ما مدير المنصة يأكد."""
    from .models import PlatformPayment
    invoice = get_object_or_404(PlatformPayment, pk=invoice_id)
    if not request.user.is_authenticated or request.user.company_id != invoice.company_id:
        return redirect("core:login")
    return render(request, "core/subscribe_invoice.html", {"invoice": invoice, "plan": invoice.company.platform_plan})


def join_subaccount(request, code):
    """صفحة الانضمام العامة بكود دعوة — بدل ما صاحب الشبكة يعمل يوزر/باسورد
    لموظفه يدويًا، بيديله الكود وهو بيسجل نفسه بنفسه هنا."""
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    invite = get_object_or_404(SubAccountInvite, code=code)
    if not invite.is_usable:
        return render(request, "core/join.html", {"invite": None, "code": code})
    if request.method == "POST":
        form = JoinSubAccountForm(request.POST)
        if form.is_valid():
            user = form.save(invite)
            login(request, user)
            return redirect("dashboard:home")
    else:
        form = JoinSubAccountForm()
    return render(request, "core/join.html", {"invite": invite, "form": form, "code": code})
