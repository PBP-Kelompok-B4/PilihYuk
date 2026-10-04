from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.urls import Resolver404, resolve
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import LoginForm, ProfileForm, RegisterForm, StyledPasswordChangeForm

REMEMBER_SECONDS = 30 * 24 * 3600

# Kartu di halaman profil. Path mengikuti navigasi header; kartu aktif sendiri saat app-nya punya URL.
PROFILE_LINKS = [
    ("Preferensi Nutrisi", "Atur nutrien yang ingin kamu prioritaskan.", "/preferensi/", False),
    ("Riwayat Keputusan", "Produk yang pernah kamu pilih beserta alasannya.", "/riwayat/", False),
    ("Shelf Saya", "Shelf buatanmu dan shelf publik yang kamu simpan.", "/shelf/saya/", False),
    ("Moderasi Data", "Tinjau pengajuan koreksi data produk.", "/moderasi/", True),
]


def safe_next(request):
    target = request.POST.get("next") or request.GET.get("next") or ""
    ok = url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure())
    return target if ok else "home_page"


def register(request):
    if request.user.is_authenticated:
        return redirect("home_page")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:  # dua pendaftaran serentak dengan email yang sama
            form.add_error("email", "Email ini sudah terdaftar. Coba masuk.")
        else:
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Akun berhasil dibuat. Selamat datang di PilihYuk!")
            return redirect(safe_next(request))
    return render(request, "accounts/register.html", {"form": form, "next": request.GET.get("next", "")})


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)  # login() juga memutar kunci sesi
        self.request.session.set_expiry(REMEMBER_SECONDS if form.cleaned_data["remember"] else 0)
        messages.success(self.request, "Berhasil masuk.")
        return response


class LogoutView(auth_views.LogoutView):  # POST saja (Django 5)
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, "Kamu sudah keluar.")
        return response


def profile_links(user):
    links = []
    for title, text, path, staff_only in PROFILE_LINKS:
        if staff_only and not user.is_staff:
            continue
        try:
            resolve(path)
            ready = True
        except Resolver404:
            ready = False
        links.append({"title": title, "text": text, "path": path, "ready": ready})
    return links


def render_profile(request, edit_form=None, password_form=None):
    user = request.user  # hanya data milik request.user; tidak ada id di URL
    return render(
        request,
        "accounts/profile.html",
        {
            "edit_form": edit_form or ProfileForm(user=user),
            "password_form": password_form or StyledPasswordChangeForm(user),
            "links": profile_links(user),
        },
    )


@login_required
def profile(request):
    return render_profile(request)


@login_required
@require_POST
def profile_edit(request):
    form = ProfileForm(request.POST, user=request.user)
    if form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error("email", "Email ini sudah dipakai akun lain.")
        else:
            messages.success(request, "Data akun diperbarui.")
            return redirect("accounts:profile")
    return render_profile(request, edit_form=form)


@login_required
@require_POST
def password_change(request):
    form = StyledPasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # sesi tidak putus
        messages.success(request, "Password diganti.")
        return redirect("accounts:profile")
    return render_profile(request, password_form=form)
