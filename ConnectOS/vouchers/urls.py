from django.urls import path

from . import views

app_name = "vouchers"

urlpatterns = [
    path("", views.batch_list, name="batch_list"),
    path("new/", views.batch_create, name="batch_create"),
    path("<int:pk>/", views.batch_detail, name="batch_detail"),
    path("<int:pk>/delete/", views.batch_delete, name="batch_delete"),
    path("<int:pk>/print/", views.batch_print, name="batch_print"),
    path("templates/", views.template_list, name="template_list"),
    path("templates/new/", views.template_create, name="template_create"),
    path("templates/<int:pk>/designer/", views.template_designer, name="template_designer"),
    path("templates/<int:pk>/designer/save/", views.template_designer_save, name="template_designer_save"),
    path("topup/", views.topup_batch_list, name="topup_batch_list"),
    path("topup/new/", views.topup_batch_create, name="topup_batch_create"),
    path("topup/<int:pk>/", views.topup_batch_detail, name="topup_batch_detail"),
    path("topup/<int:pk>/delete/", views.topup_batch_delete, name="topup_batch_delete"),
]
