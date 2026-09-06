from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render

from core.limits import check_server_limit

from .content_filter import build_fair_share_queue_script, build_mandatory_content_filter_script
from .forms import NASServerForm
from .models import NASServer
from .services import MikroTikService


@login_required
def nas_list(request):
    company = request.user.company
    servers = NASServer.objects.filter(company=company)
    return render(request, "nas_manager/list.html", {"servers": servers})


@login_required
def nas_create(request):
    company = request.user.company
    limit = company.effective_max_servers
    current_count = NASServer.objects.filter(company=company).count()
    usage_hint = {"current": current_count, "limit": limit} if limit is not None else None
    if request.method == "POST":
        form = NASServerForm(request.POST)
        if form.is_valid():
            limit_error = check_server_limit(company)
            if limit_error:
                messages.error(request, limit_error)
                return render(request, "nas_manager/form.html", {"form": form, "usage_hint": usage_hint})
            nas = form.save(commit=False)
            nas.company = company
            nas.save()
            messages.success(request, f'تمت إضافة الجهاز "{nas.name}" بنجاح.')
            return redirect("nas_manager:list")
    else:
        form = NASServerForm()
    return render(request, "nas_manager/form.html", {"form": form, "usage_hint": usage_hint})


@login_required
def nas_delete(request, pk):
    nas = get_object_or_404(NASServer, pk=pk, company=request.user.company)
    if request.method == "POST":
        name = nas.name
        nas.soft_delete()
        messages.success(request, f'تم نقل الجهاز "{name}" لسلة المهملات.')
        return redirect("nas_manager:list")
    return render(request, "nas_manager/confirm_delete.html", {"nas": nas})


@login_required
def nas_test_connection(request, pk):
    """يحاول الاتصال الفعلي بالجهاز عن طريق RouterOS API ويحدّث حالته."""
    nas = get_object_or_404(NASServer, pk=pk, company=request.user.company)
    if request.method == "POST":
        ok, msg = MikroTikService(nas).test_connection()
        if ok:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return redirect("nas_manager:list")


@login_required
def nas_setup_script(request, pk):
    """سكريبت RouterOS جاهز للصق في Winbox — بيضبط الجهاز يوجّه مصادقة
    الهوت سبوت لسيرفر RADIUS المركزي بتاع المنصة تلقائيًا (بنفس فكرة زرار
    "من هنا" في Smart Radius)، وكمان بيفتح نفق SSTP للرجوع للخارج عشان
    "فتح الأجهزة" يشتغل حتى لو الراوتر خلف NAT بدون IP عام."""
    nas = get_object_or_404(NASServer, pk=pk, company=request.user.company)
    nas.ensure_vpn_credentials()
    base_script = f"""/radius
add service=hotspot address={settings.RADIUS_SERVER_HOST} secret="{nas.secret}" authentication-port=1812 accounting-port=1813 timeout=3s

/ip hotspot profile
set [find default=yes] use-radius=yes

/interface sstp-client
add name=connectos-vpn connect-to={settings.VPN_PUBLIC_HOST} user="{nas.vpn_username}" password="{nas.vpn_password}" profile=default-encryption disabled=no

/ip service
set api port=8728 disabled=no

:log info "ConnectOS: تم ربط الجهاز '{nas.name}' بسيرفر RADIUS وفتح نفق VPN بنجاح"
"""
    # الفقرتين التاليتين بيتلزقوا إجباريًا مع كل جهاز جديد — مفيش أي شرط
    # أو حقل إعداد في الداشبورد بيقدر يمنع لزقهم. حجب المحتوى الإباحي هنا
    # إعداد أساسي غير قابل للإلغاء إطلاقًا، وطابور التوزيع العادل بيتجهز
    # جاهز على الجهاز عشان أي باقة تستخدمه وقت ما صاحب الشبكة يفعّله عليها.
    script = "\n\n".join([
        base_script.strip("\n"),
        build_mandatory_content_filter_script(),
        build_fair_share_queue_script(),
    ]) + "\n"
    return render(request, "nas_manager/setup_script.html", {"nas": nas, "script": script})


@login_required
def device_unlock_list(request):
    """فتح الأجهزة — قائمة كل السيرفرات مع حالة نفق الـ VPN بتاع كل واحد،
    نفس فكرة قائمة "فتح الاجهزة" عند Smart Radius."""
    servers = NASServer.objects.filter(company=request.user.company)
    return render(request, "nas_manager/device_unlock_list.html", {"servers": servers})


@login_required
def device_unlock(request, pk):
    """بيانات نفق VPN لجهاز واحد — يوزر/باسورد/بورت النفق المخصص، بالظبط
    زي شاشة "Smart VPN" عند Smart Radius. ملحوظة أمانة مهمة: الصفحة دي
    وطبقة البيانات ورا كل ده حقيقية وشغالة، لكن تشغيل النفق فعليًا محتاج
    سيرفر VPN حقيقي شغال (SoftEther/OpenVPN) يستقبل الاتصال ده — شوف
    VPN_SETUP.md لخطوات تجهيزه، ده مش حاجة كود Django بيقدر يعملها لوحده."""
    nas = get_object_or_404(NASServer, pk=pk, company=request.user.company)
    nas.ensure_vpn_credentials()
    return render(request, "nas_manager/device_unlock.html", {"nas": nas})
