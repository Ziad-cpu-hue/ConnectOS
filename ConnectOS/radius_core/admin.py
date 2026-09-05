from django.contrib import admin

from .models import RadAcct, RadCheck, RadNas, RadReply

admin.site.register(RadCheck)
admin.site.register(RadReply)
admin.site.register(RadNas)
admin.site.register(RadAcct)
