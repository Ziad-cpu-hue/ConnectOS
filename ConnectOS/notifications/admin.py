from django.contrib import admin

from .models import NotificationLog, NotificationSettings

admin.site.register(NotificationSettings)
admin.site.register(NotificationLog)
