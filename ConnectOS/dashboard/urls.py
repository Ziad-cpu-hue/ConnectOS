from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("platform/", views.platform_overview, name="platform_overview"),
    path("platform/payments/<int:payment_id>/confirm/", views.confirm_payment, name="confirm_payment"),
    path("platform/companies/<int:company_id>/limits/", views.company_limits, name="company_limits"),
    path("team/", views.team, name="team"),
    path("team/invites/<int:invite_id>/revoke/", views.revoke_invite, name="revoke_invite"),
    path("trash/", views.trash, name="trash"),
    path("trash/<str:section>/<int:pk>/restore/", views.trash_restore, name="trash_restore"),
    path("trash/<str:section>/<int:pk>/delete/", views.trash_delete_forever, name="trash_delete_forever"),
    path("settings/", views.settings_view, name="settings"),
    path("statistics/", views.statistics_view, name="statistics"),
    path("consumption/", views.consumption_view, name="consumption"),
    path("profile/", views.profile_view, name="profile"),
]
