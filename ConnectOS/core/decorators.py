"""ديكوريتورز صلاحيات مركزية تُستخدم في أكتر من تطبيق."""
from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied


def platform_admin_required(view_func):
    """يسمح فقط لمستخدم بصلاحية platform_admin بالدخول. أي حد غيره ياخد 403،
    مش بس إخفاء الرابط من القائمة الجانبية (كان ده الثغرة الأصلية)."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role != "platform_admin":
            raise PermissionDenied("هذه الصفحة مخصصة لمدير المنصة فقط.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def company_required(view_func):
    """تأكيد إن المستخدم مرتبط بشركة قبل السماح له بأي شاشة إدارية."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.company_id is None:
            raise PermissionDenied("حسابك غير مرتبط بأي شركة.")
        return view_func(request, *args, **kwargs)

    return _wrapped
