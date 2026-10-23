from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView  # POST saja (Django 5)
from django.urls import path, reverse_lazy

from . import views
from .forms import StyledPasswordResetForm, StyledSetPasswordForm

app_name = "accounts"

urlpatterns = [
    path("daftar/", views.register, name="register"),
    path("masuk/", views.LoginView.as_view(), name="login"),
    path("keluar/", LogoutView.as_view(), name="logout"),
    path("profil/", views.profile, name="profile"),
    path("profil/ubah/", views.profile_edit, name="profile_edit"),
    path("profil/password/", views.password_change, name="password"),
    path("lupa-password/", auth_views.PasswordResetView.as_view(
        form_class=StyledPasswordResetForm,
        template_name="accounts/password_reset_form.html",
        email_template_name="accounts/password_reset_email.txt",
        subject_template_name="accounts/password_reset_subject.txt",
        success_url=reverse_lazy("accounts:password_reset_done"),
    ), name="password_reset"),
    path("lupa-password/terkirim/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html",
    ), name="password_reset_done"),
    path("lupa-password/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        form_class=StyledSetPasswordForm,
        template_name="accounts/password_reset_confirm.html",
        success_url=reverse_lazy("accounts:password_reset_complete"),
    ), name="password_reset_confirm"),
    path("lupa-password/selesai/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html",
    ), name="password_reset_complete"),
]
