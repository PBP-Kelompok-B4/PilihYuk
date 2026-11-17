from django.contrib.auth import login as auth_login, logout as auth_logout
from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.forms import LoginForm, RegisterForm

# Ketiga view memakai authentication_classes([]): tanpa sesi yang dikenali, DRF tidak memeriksa CSRF,
# jadi pbp_django_auth (yang tidak mengirim token CSRF) bisa memanggilnya tanpa @csrf_exempt.


def user_data(user):
    # Username adalah email, jadi tidak pernah dikirim balik.
    return {"display_name": user.first_name or "Pengguna", "is_staff": user.is_staff}


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    form = LoginForm(request._request, data=request.data)
    if not form.is_valid():
        message = " ".join(form.non_field_errors()) or "Email dan password wajib diisi."
        return Response({"status": False, "message": message}, status=status.HTTP_401_UNAUTHORIZED)
    user = form.get_user()
    auth_login(request._request, user)
    return Response({"status": True, "message": "Berhasil masuk.", **user_data(user)})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def register(request):
    form = RegisterForm(request.data)
    if form.is_valid():
        try:
            user = form.save()
        except IntegrityError:  # dua pendaftaran serentak dengan email yang sama
            form.add_error("email", "Email ini sudah terdaftar. Coba masuk.")
        else:
            return Response(
                {"status": True, "message": "Akun berhasil dibuat.", **user_data(user)},
                status=status.HTTP_201_CREATED,
            )
    return Response({"status": False, "errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def logout(request):
    auth_logout(request._request)
    return Response({"status": True, "message": "Berhasil keluar."})
