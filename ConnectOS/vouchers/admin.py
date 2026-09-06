from django.contrib import admin

from .models import Voucher, VoucherBatch, VoucherTemplate


@admin.register(VoucherTemplate)
class VoucherTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "primary_color", "secondary_color", "is_default")


@admin.register(VoucherBatch)
class VoucherBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "plan", "quantity", "created_at")
    list_filter = ("company", "plan")


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ("code", "batch", "plan", "status", "activated_at", "expires_at")
    list_filter = ("status", "plan")
    search_fields = ("code",)
