from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from accounts.tests import PASSWORD, make_user, register_data

User = get_user_model()


class AuthApiTests(APITestCase):
    def setUp(self):
        # pbp_django_auth tidak mengirim token CSRF, jadi tes memakai klien yang tetap memeriksanya.
        self.client = APIClient(enforce_csrf_checks=True)

    def test_login_sets_session_without_csrf_or_email(self):
        make_user()
        r = self.client.post(reverse("accounts_api:login"), {"username": "rani@email.com", "password": PASSWORD})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": True, "message": "Berhasil masuk.", "display_name": "Rani Ayu", "is_staff": False})
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_wrong_password_is_401(self):
        make_user()
        r = self.client.post(reverse("accounts_api:login"), {"username": "rani@email.com", "password": "salah123"})
        self.assertEqual(r.status_code, 401)
        self.assertFalse(r.json()["status"])
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_register_creates_user_and_rejects_duplicate(self):
        r = self.client.post(reverse("accounts_api:register"), register_data())
        self.assertEqual(r.status_code, 201)
        self.assertTrue(User.objects.filter(username="rani@email.com", first_name="Rani Ayu").exists())
        r = self.client.post(reverse("accounts_api:register"), register_data())
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.json()["errors"])

    def test_logout_ends_session(self):
        make_user()
        self.client.post(reverse("accounts_api:login"), {"username": "rani@email.com", "password": PASSWORD})
        r = self.client.post(reverse("accounts_api:logout"))
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(reverse("accounts_api:login")).status_code, 405)
