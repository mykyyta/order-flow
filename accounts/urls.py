from django.urls import path

from .views import auth_login, auth_logout, change_password, profile_view

urlpatterns = [
    path("login/", auth_login, name="auth_login"),
    path("logout/", auth_logout, name="auth_logout"),
    path("profile/", profile_view, name="profile"),
    path("profile/change-password/", change_password, name="change_password"),
]
