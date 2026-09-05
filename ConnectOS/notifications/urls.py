from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.settings_view, name="settings"),
    path("test/", views.send_test, name="send_test"),
]
