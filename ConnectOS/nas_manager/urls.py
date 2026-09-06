from django.urls import path

from . import views

app_name = "nas_manager"

urlpatterns = [
    path("", views.nas_list, name="list"),
    path("new/", views.nas_create, name="create"),
    path("<int:pk>/delete/", views.nas_delete, name="delete"),
    path("<int:pk>/test/", views.nas_test_connection, name="test_connection"),
    path("<int:pk>/script/", views.nas_setup_script, name="setup_script"),
    path("unlock/", views.device_unlock_list, name="device_unlock_list"),
    path("unlock/<int:pk>/", views.device_unlock, name="device_unlock"),
]
