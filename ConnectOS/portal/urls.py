from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("login/", views.portal_login, name="login"),
    path("logout/", views.portal_logout, name="logout"),
    path("", views.portal_dashboard, name="dashboard"),
    path("renew/", views.portal_renew, name="renew"),
    path("redeem/", views.portal_redeem_topup, name="redeem_topup"),
]
