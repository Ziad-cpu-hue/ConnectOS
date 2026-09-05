from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.audit import log_action
from core.limits import check_subscriber_limit

from .forms import SubscriberForm, SubscriberGroupForm
from .models import Subscriber, SubscriberGroup


@login_required
def subscriber_list(request):
    company = request.user.company
    q = request.GET.get("q", "").strip()
    plan_id = request.GET.get("plan", "")
    group_id = request.GET.get("group", "")
    status = request.GET.get("status", "")

    subscribers = Subscriber.objects.filter(company=company).select_related("plan", "group")
    if q:
        subscribers = subscribers.filter(username__icontains=q) | subscribers.filter(full_name__icontains=q)
    if plan_id:
        subscribers = subscribers.filter(plan_id=plan_id)
    if group_id:
        subscribers = subscribers.filter(group_id=group_id)
    if status:
        subscribers = subscribers.filter(status=status)

    from plans.models import Plan
    return render(request, "subscribers/list.html", {
        "subscribers": subscribers, "q": q,
        "plans": Plan.objects.filter(company=company),
        "groups": SubscriberGroup.objects.filter(company=company),
        "plan_id": plan_id, "group_id": group_id, "status": status,
    })


@login_required
def group_list(request):
    company = request.user.company
    groups = SubscriberGroup.objects.filter(company=company)
    if request.method == "POST":
        form = SubscriberGroupForm(request.POST)
        if form.is_valid():
            g = form.save(commit=False)
            g.company = company
            g.save()
            messages.success(request, f'تمت إضافة مجموعة "{g.name}".')
            return redirect("subscribers:group_list")
    else:
        form = SubscriberGroupForm()
    return render(request, "subscribers/group_list.html", {"groups": groups, "form": form})


@login_required
def group_delete(request, pk):
    company = request.user.company
    group = get_object_or_404(SubscriberGroup, pk=pk, company=company)
    if request.method == "POST":
        group.subscribers.update(group=None)
        group.delete()
        messages.success(request, "تم حذف المجموعة (المشتركون فيها بقوا بدون مجموعة).")
    return redirect("subscribers:group_list")


@login_required
def subscriber_create(request):
    company = request.user.company
    limit = company.effective_max_clients
    current_count = Subscriber.objects.filter(company=company).count()
    usage_hint = {"current": current_count, "limit": limit} if limit is not None else None
    if request.method == "POST":
        form = SubscriberForm(request.POST, company=company)
        if form.is_valid():
            limit_error = check_subscriber_limit(company)
            if limit_error:
                messages.error(request, limit_error)
                return render(request, "subscribers/form.html", {"form": form, "is_new": True, "usage_hint": usage_hint})
            sub = form.save(commit=False)
            sub.company = company
            sub.save()
            messages.success(request, "تمت إضافة المشترك وتفعيله على RADIUS فورًا.")
            return redirect("subscribers:list")
    else:
        form = SubscriberForm(company=company)
    return render(request, "subscribers/form.html", {"form": form, "is_new": True, "usage_hint": usage_hint})


@login_required
def subscriber_edit(request, pk):
    company = request.user.company
    sub = get_object_or_404(Subscriber, pk=pk, company=company)
    if request.method == "POST":
        form = SubscriberForm(request.POST, instance=sub, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات المشترك.")
            return redirect("subscribers:list")
    else:
        form = SubscriberForm(instance=sub, company=company)
    return render(request, "subscribers/form.html", {"form": form, "is_new": False, "sub": sub})


@login_required
def subscriber_renew(request, pk):
    company = request.user.company
    sub = get_object_or_404(Subscriber, pk=pk, company=company)
    if request.method == "POST":
        sub.renew()
        messages.success(request, f"تم تجديد اشتراك {sub.full_name} لمدة {sub.plan.duration_days} يوم.")
    return redirect("subscribers:list")


@login_required
def subscriber_toggle_suspend(request, pk):
    company = request.user.company
    sub = get_object_or_404(Subscriber, pk=pk, company=company)
    if request.method == "POST":
        sub.status = "active" if sub.status == "suspended" else "suspended"
        sub.save()
        messages.success(request, "تم تحديث حالة المشترك.")
    return redirect("subscribers:list")


@login_required
def subscriber_delete(request, pk):
    company = request.user.company
    sub = get_object_or_404(Subscriber, pk=pk, company=company)
    if request.method == "POST":
        sub.soft_delete()
        log_action(request, "نقل مشترك لسلة المهملات", f"{sub.full_name} ({sub.username})")
        messages.success(request, "تم نقل المشترك لسلة المهملات (اتقفل على RADIUS فورًا، وتقدر تسترجعه في أي وقت).")
    return redirect("subscribers:list")
