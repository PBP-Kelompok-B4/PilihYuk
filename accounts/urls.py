from django.contrib.auth.views import LogoutView  # POST saja (Django 5)
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("daftar/", views.register, name="register"),
    path("masuk/", views.LoginView.as_view(), name="login"),
    path("keluar/", LogoutView.as_view(), name="logout"),
    path("profil/", views.profile, name="profile"),
    path("profil/ubah/", views.profile_edit, name="profile_edit"),
    path("profil/password/", views.password_change, name="password"),
]
