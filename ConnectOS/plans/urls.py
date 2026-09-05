from django.urls import path

from . import views

app_name = "plans"

urlpatterns = [
    path("", views.plan_list, name="list"),
    path("new/", views.plan_create, name="create"),
    path("<int:pk>/delete/", views.plan_delete, name="delete"),
]
