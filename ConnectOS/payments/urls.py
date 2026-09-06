from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("", views.checkout, name="checkout"),
    path("webhook/paymob/", views.paymob_webhook, name="paymob_webhook"),
]
