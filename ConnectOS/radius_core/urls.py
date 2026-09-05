from django.urls import path

from . import views

app_name = "radius_core"

urlpatterns = [
    path("accounting/", views.accounting_webhook, name="accounting_webhook"),
    path("online/", views.online_now, name="online_now"),
]
