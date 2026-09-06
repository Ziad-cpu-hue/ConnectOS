from functools import wraps

from django.shortcuts import redirect

from subscribers.models import Subscriber


def subscriber_login_required(view_func):
    """جلسة منفصلة تمامًا عن حسابات الشركة (core.User) — العميل النهائي
    مش عنده حساب Django User، بيدخل بيوزر/باسورد الهوت سبوت بتاعته فقط."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        sub_id = request.session.get("portal_subscriber_id")
        if not sub_id:
            return redirect("portal:login")
        try:
            request.subscriber = Subscriber.objects.select_related("company", "plan").get(pk=sub_id)
        except Subscriber.DoesNotExist:
            request.session.flush()
            return redirect("portal:login")
        return view_func(request, *args, **kwargs)

    return _wrapped
