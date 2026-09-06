from django.contrib import admin

from .models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "quota_mb", "duration_days", "price", "is_active")
    list_filter = ("company", "is_active")
