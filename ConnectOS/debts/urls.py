from django.urls import path

from . import views

app_name = "debts"

urlpatterns = [
    path("", views.reseller_list, name="reseller_list"),
    path("new/", views.reseller_create, name="reseller_create"),
    path("<int:pk>/", views.reseller_detail, name="reseller_detail"),
    path("<int:pk>/delete/", views.reseller_delete, name="reseller_delete"),
    path("<int:pk>/deliver/", views.deliver_cards, name="deliver_cards"),
    path("<int:pk>/payment/", views.record_payment, name="record_payment"),
]
