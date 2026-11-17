from django.urls import path

from accounts import api_views

app_name = "accounts_api"

urlpatterns = [
    path("login/", api_views.login, name="login"),
    path("register/", api_views.register, name="register"),
    path("logout/", api_views.logout, name="logout"),
]
