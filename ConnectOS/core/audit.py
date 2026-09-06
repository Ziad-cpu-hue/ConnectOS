from .models import AuditLog


def log_action(request, action, details=""):
    """Helper بسيط يُستخدم من أي view حساس لتسجيل العملية في سجل التدقيق."""
    AuditLog.objects.create(
        company=getattr(request.user, "company", None),
        user=request.user if request.user.is_authenticated else None,
        action=action,
        details=details,
    )
