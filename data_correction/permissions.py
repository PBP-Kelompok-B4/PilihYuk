"""Permission API Modul Antrean Data. Keduanya tetap 403 (SessionAuthentication), tetapi dengan code."""
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import IsAdminUser, IsAuthenticated

AUTH_REQUIRED = {"detail": "Silakan masuk terlebih dahulu.", "code": "authentication_required"}
FORBIDDEN = {"detail": "Halaman ini khusus kurator.", "code": "forbidden"}


class LoggedIn(IsAuthenticated):
    """IsAuthenticated, tetapi pengunjung mendapat body AUTH_REQUIRED."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            raise NotAuthenticated(AUTH_REQUIRED)
        return True


class Curator(IsAdminUser):
    """IsAdminUser sudah memeriksa is_staff, sama dengan staff_required di web; hanya pesannya diganti.
    Dipasang setelah LoggedIn, supaya pengunjung mendapat AUTH_REQUIRED, bukan pesan bawaan DRF."""

    message = FORBIDDEN