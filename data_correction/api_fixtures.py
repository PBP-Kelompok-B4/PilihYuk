"""Helper bersama untuk tes API Modul 4 (tests_api*.py).

Notes:
- Bukan file tes. Namanya sengaja tidak diawali "test", jadi tidak ikut dijalankan
  `manage.py test`.
- Klien selalu APIClient(enforce_csrf_checks=True): pbp_django_auth di aplikasi tidak mengirim
  token CSRF sendiri, jadi tes juga harus memeriksanya.
- Masuk memakai force_login, bukan client.login, karena django-axes membuat client.login gagal.
"""
from django.urls import reverse
from rest_framework.test import APIClient


def api_client(user=None):
    """APIClient yang memeriksa CSRF; sudah masuk sebagai user bila diberikan.

    Contoh:
        api_client()       -> klien pengunjung
        api_client(budi)   -> klien yang sudah masuk sebagai budi
    """
    client = APIClient(enforce_csrf_checks=True)
    if user is not None:
        client.force_login(user)
    return client


def csrf_token(client):
    """Token CSRF untuk klien itu, diambil seperti Tutorial 07: buka halaman Browsable API
    (HTTP_ACCEPT="text/html"), lalu baca cookie csrftoken yang dipasang halaman itu.
    Panggil setelah force_login. Kirim hasilnya sebagai HTTP_X_CSRFTOKEN.

    Contoh:
        token = csrf_token(client)
        client.post(url, body, format="json", HTTP_X_CSRFTOKEN=token)
    """
    page = client.get(reverse("data_correction_api:contribution_queue"), HTTP_ACCEPT="text/html")
    if page.status_code != 200 or "csrftoken" not in client.cookies:
        raise AssertionError("Halaman Browsable API tidak memasang cookie csrftoken.")
    return client.cookies["csrftoken"].value