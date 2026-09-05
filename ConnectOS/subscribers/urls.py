from django.urls import path

from . import views

app_name = "subscribers"

urlpatterns = [
    path("", views.subscriber_list, name="list"),
    path("groups/", views.group_list, name="group_list"),
    path("groups/<int:pk>/delete/", views.group_delete, name="group_delete"),
    path("new/", views.subscriber_create, name="create"),
    path("<int:pk>/edit/", views.subscriber_edit, name="edit"),
    path("<int:pk>/renew/", views.subscriber_renew, name="renew"),
    path("<int:pk>/toggle/", views.subscriber_toggle_suspend, name="toggle_suspend"),
    path("<int:pk>/delete/", views.subscriber_delete, name="delete"),
]
