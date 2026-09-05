from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DeliverCardsForm, PaymentForm, ResellerForm
from .models import DebtTransaction, Reseller


@login_required
def reseller_list(request):
    resellers = Reseller.objects.filter(company=request.user.company)
    total_debt = sum(r.current_debt for r in resellers)
    over_limit_count = sum(1 for r in resellers if r.is_over_limit)
    return render(request, "debts/reseller_list.html", {
        "resellers": resellers,
        "total_debt": total_debt,
        "over_limit_count": over_limit_count,
    })


@login_required
def reseller_create(request):
    if request.method == "POST":
        form = ResellerForm(request.POST)
        if form.is_valid():
            reseller = form.save(commit=False)
            reseller.company = request.user.company
            reseller.save()
            messages.success(request, f'تمت إضافة الموزع "{reseller.name}".')
            return redirect("debts:reseller_list")
    else:
        form = ResellerForm()
    return render(request, "debts/reseller_form.html", {"form": form})


@login_required
def reseller_detail(request, pk):
    reseller = get_object_or_404(Reseller, pk=pk, company=request.user.company)
    transactions = reseller.transactions.all()
    return render(request, "debts/reseller_detail.html", {"reseller": reseller, "transactions": transactions})


@login_required
def reseller_delete(request, pk):
    reseller = get_object_or_404(Reseller, pk=pk, company=request.user.company)
    if request.method == "POST":
        reseller.soft_delete()
        messages.success(request, f'تم نقل الموزع "{reseller.name}" لسلة المهملات.')
    return redirect("debts:reseller_list")


@login_required
def deliver_cards(request, pk):
    reseller = get_object_or_404(Reseller, pk=pk, company=request.user.company)
    company = request.user.company
    if request.method == "POST":
        form = DeliverCardsForm(request.POST, company=company)
        if form.is_valid():
            batch = form.cleaned_data["voucher_batch"]
            amount = batch.plan.price * batch.quantity
            DebtTransaction.objects.create(
                reseller=reseller, type="card_delivery", amount=amount,
                voucher_batch=batch, note=form.cleaned_data["note"], created_by=request.user,
            )
            messages.success(request, f"تم تسجيل تسليم {batch.quantity} كارت بقيمة {amount} ج على حساب {reseller.name}.")
            return redirect("debts:reseller_detail", pk=reseller.pk)
    else:
        form = DeliverCardsForm(company=company)
    return render(request, "debts/deliver_cards.html", {"form": form, "reseller": reseller})


@login_required
def record_payment(request, pk):
    reseller = get_object_or_404(Reseller, pk=pk, company=request.user.company)
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            DebtTransaction.objects.create(
                reseller=reseller, type="payment", amount=form.cleaned_data["amount"],
                payment_method=form.cleaned_data["payment_method"],
                note=form.cleaned_data["note"], created_by=request.user,
            )
            messages.success(request, f"تم تسجيل سداد {form.cleaned_data['amount']} ج من {reseller.name}.")
            return redirect("debts:reseller_detail", pk=reseller.pk)
    else:
        form = PaymentForm()
    return render(request, "debts/record_payment.html", {"form": form, "reseller": reseller})
