from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Company, PlatformPayment, PlatformPlan, User


@admin.register(PlatformPlan)
class PlatformPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "max_clients", "max_servers", "max_print_cards", "price_monthly", "is_featured", "is_active", "order")
    list_editable = ("is_featured", "is_active", "order")
    ordering = ("order",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "platform_plan", "monthly_fee", "is_active", "created_at")
    list_filter = ("platform_plan", "is_active")
    search_fields = ("name",)


@admin.register(PlatformPayment)
class PlatformPaymentAdmin(admin.ModelAdmin):
    list_display = ("company", "amount", "method", "is_confirmed", "paid_at")
    list_filter = ("method", "is_confirmed")


@admin.register(User)
class ConnectOSUserAdmin(UserAdmin):
    list_display = ("username", "email", "company", "role", "is_active")
    list_filter = ("role", "company")
    fieldsets = UserAdmin.fieldsets + (
        ("بيانات ConnectOS", {"fields": ("company", "role", "phone", "last_login_ip")}),
    )
