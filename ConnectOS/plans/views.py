from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PlanForm
from .models import Plan


@login_required
def plan_list(request):
    plans = Plan.objects.filter(company=request.user.company)
    return render(request, "plans/list.html", {"plans": plans})


@login_required
def plan_create(request):
    if request.method == "POST":
        form = PlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.company = request.user.company
            plan.save()
            messages.success(request, f'تم إنشاء باقة "{plan.name}" بنجاح.')
            return redirect("plans:list")
    else:
        form = PlanForm()
    return render(request, "plans/form.html", {"form": form})


@login_required
def plan_delete(request, pk):
    plan = get_object_or_404(Plan, pk=pk, company=request.user.company)
    if request.method == "POST":
        plan.delete()
        messages.success(request, "تم حذف الباقة.")
        return redirect("plans:list")
    return render(request, "plans/confirm_delete.html", {"plan": plan})
