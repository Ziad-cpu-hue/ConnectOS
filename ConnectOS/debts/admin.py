from django.contrib import admin

from .models import DebtTransaction, Reseller


@admin.register(Reseller)
class ResellerAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "phone", "current_debt", "debt_limit", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("name", "phone")


@admin.register(DebtTransaction)
class DebtTransactionAdmin(admin.ModelAdmin):
    list_display = ("reseller", "type", "amount", "created_at", "created_by")
    list_filter = ("type",)
