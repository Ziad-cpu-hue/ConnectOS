from django.contrib import admin

from .models import NASServer


@admin.register(NASServer)
class NASServerAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "ip_address", "is_online", "last_seen")
    list_filter = ("company", "is_online")
    search_fields = ("name", "ip_address")
