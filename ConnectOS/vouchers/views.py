from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

from core.limits import check_print_cards_limit, cards_printed_this_month

from .forms import TopupBatchForm, VoucherBatchForm, VoucherTemplateForm
from .models import TopupBatch, Voucher, VoucherBatch, VoucherTemplate
from .qr_utils import voucher_qr_base64


@login_required
def batch_list(request):
    batches = VoucherBatch.objects.filter(company=request.user.company).select_related("plan")
    return render(request, "vouchers/batch_list.html", {"batches": batches})


@login_required
def batch_create(request):
    company = request.user.company
    limit = company.effective_max_print_cards
    used_this_month = cards_printed_this_month(company)
    usage_hint = {"current": used_this_month, "limit": limit} if limit is not None else None
    if request.method == "POST":
        form = VoucherBatchForm(request.POST, company=company)
        if form.is_valid():
            limit_error = check_print_cards_limit(company, form.cleaned_data["quantity"])
            if limit_error:
                messages.error(request, limit_error)
                return render(request, "vouchers/batch_form.html", {"form": form, "usage_hint": usage_hint})
            batch = form.save(commit=False)
            batch.company = company
            batch.created_by = request.user
            batch.save()
            batch.generate_vouchers()
            messages.success(request, f"تم توليد {batch.quantity} كارت بنجاح.")
            return redirect("vouchers:batch_detail", pk=batch.pk)
    else:
        form = VoucherBatchForm(company=company)
    return render(request, "vouchers/batch_form.html", {"form": form, "usage_hint": usage_hint})


@login_required
def batch_detail(request, pk):
    batch = get_object_or_404(VoucherBatch, pk=pk, company=request.user.company)
    vouchers = batch.vouchers.all()
    return render(request, "vouchers/batch_detail.html", {"batch": batch, "vouchers": vouchers})


@login_required
def batch_delete(request, pk):
    batch = get_object_or_404(VoucherBatch, pk=pk, company=request.user.company)
    if request.method == "POST":
        batch.soft_delete()
        messages.success(request, "تم نقل دفعة الكروت لسلة المهملات.")
    return redirect("vouchers:batch_list")


@login_required
def batch_print(request, pk):
    batch = get_object_or_404(VoucherBatch, pk=pk, company=request.user.company)
    vouchers = batch.vouchers.all()
    template = batch.template
    layout = template.get_layout() if template else None
    vouchers_with_qr = [
        {"voucher": v, "qr": voucher_qr_base64(v) if (template and template.show_qr) else None}
        for v in vouchers
    ]
    return render(request, "vouchers/print_sheet.html", {
        "batch": batch, "vouchers_with_qr": vouchers_with_qr, "template": template, "layout": layout,
    })


@login_required
def template_list(request):
    templates = VoucherTemplate.objects.filter(company=request.user.company)
    return render(request, "vouchers/template_list.html", {"templates": templates})


@login_required
def template_create(request):
    if request.method == "POST":
        form = VoucherTemplateForm(request.POST, request.FILES)
        if form.is_valid():
            tpl = form.save(commit=False)
            tpl.company = request.user.company
            tpl.save()
            messages.success(request, f'تم حفظ قالب "{tpl.name}". دلوقتي افتح مصمم السحب والإفلات لترتيب العناصر.')
            return redirect("vouchers:template_designer", pk=tpl.pk)
    else:
        form = VoucherTemplateForm()
    return render(request, "vouchers/template_form.html", {"form": form})


@login_required
def template_designer(request, pk):
    """مصمم سحب وإفلات حقيقي: بيحرك عناصر (سيريال، سعر، شعار، QR) فوق
    معاينة الكارت، ولما يضغط حفظ بيبعت مواضعهم X/Y كـ JSON للباك إند."""
    tpl = get_object_or_404(VoucherTemplate, pk=pk, company=request.user.company)
    return render(request, "vouchers/template_designer.html", {
        "tpl": tpl, "layout": tpl.get_layout(),
    })


@login_required
@require_POST
def template_designer_save(request, pk):
    tpl = get_object_or_404(VoucherTemplate, pk=pk, company=request.user.company)
    try:
        layout = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "بيانات غير صالحة"}, status=400)
    tpl.layout_json = json.dumps(layout)
    tpl.save(update_fields=["layout_json"])
    return JsonResponse({"ok": True})


# ============================= كروت شحن الرصيد =============================

@login_required
def topup_batch_list(request):
    batches = TopupBatch.objects.filter(company=request.user.company).order_by("-created_at")
    return render(request, "vouchers/topup_batch_list.html", {"batches": batches})


@login_required
def topup_batch_create(request):
    company = request.user.company
    if request.method == "POST":
        form = TopupBatchForm(request.POST)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.company = company
            batch.created_by = request.user
            batch.save()
            batch.generate_cards()
            messages.success(request, f"تم توليد {batch.quantity} كارت شحن بقيمة {batch.amount} ج لكل كارت.")
            return redirect("vouchers:topup_batch_detail", pk=batch.pk)
    else:
        form = TopupBatchForm()
    return render(request, "vouchers/topup_batch_form.html", {"form": form})


@login_required
def topup_batch_detail(request, pk):
    batch = get_object_or_404(TopupBatch, pk=pk, company=request.user.company)
    cards = batch.cards.all()
    return render(request, "vouchers/topup_batch_detail.html", {"batch": batch, "cards": cards})


@login_required
def topup_batch_delete(request, pk):
    batch = get_object_or_404(TopupBatch, pk=pk, company=request.user.company)
    if request.method == "POST":
        batch.soft_delete()
        messages.success(request, "تم نقل دفعة كروت الشحن لسلة المهملات.")
    return redirect("vouchers:topup_batch_list")
