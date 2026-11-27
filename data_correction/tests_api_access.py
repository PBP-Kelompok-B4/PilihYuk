"""Tes akses API: body 403 dari permissions.py, galat CSRF tanpa code, dan GET me/."""
from datetime import timedelta

from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .api_fixtures import api_client, csrf_token
from .constants import PENDING
from .permissions import AUTH_REQUIRED
from .tests import make_complete_product, make_correction, make_staff, make_user

ME_URL = "/api/v1/corrections/me/"


class AccessApiTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_complete_product()
        self.correction = make_correction(self.product, self.user, brand=PENDING)

    def logged_in_endpoints(self):
        detail = reverse("data_correction_api:correction_detail", args=[self.correction.pk])
        return [
            ("get", reverse("data_correction_api:correction_form", args=[self.product.pk])),
            ("get", reverse("data_correction_api:my_corrections")),
            ("post", reverse("data_correction_api:my_corrections")),
            ("get", detail),
            ("delete", detail),
        ]

    def test_visitor_gets_authentication_required(self):
        visitor = api_client()
        token = csrf_token(visitor)
        for method, url in self.logged_in_endpoints():
            with self.subTest(method=method, url=url):
                response = getattr(visitor, method)(url, {}, format="json", HTTP_X_CSRFTOKEN=token)
                self.assertEqual((response.status_code, response.json()), (403, AUTH_REQUIRED))

    def test_csrf_failure_has_no_code(self):
        url = reverse("data_correction_api:my_corrections")
        response = api_client(self.user).post(url, {}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF", response.json()["detail"])
        self.assertNotIn("code", response.json())

    def test_me_for_visitor_user_and_curator(self):
        cases = [
            (api_client(), {"logged_in": False, "is_staff": False}),
            (api_client(self.user), {"logged_in": True, "is_staff": False}),
            (api_client(make_staff()), {"logged_in": True, "is_staff": True}),
        ]
        for client, body in cases:
            with self.subTest(body=body):
                response = client.get(ME_URL)
                self.assertEqual((response.status_code, response.json()), (200, body))

    def test_me_after_session_expired(self):
        client = api_client(self.user)
        self.assertTrue(client.get(ME_URL).json()["logged_in"])
        Session.objects.update(expire_date=timezone.now() - timedelta(minutes=1))
        self.assertEqual(client.get(ME_URL).json(), {"logged_in": False, "is_staff": False})

    def test_me_only_allows_get(self):
        self.assertEqual(reverse("data_correction_api:me"), ME_URL)
        self.assertEqual(api_client().post(ME_URL).status_code, 405)
        client = api_client(self.user)
        self.assertEqual(client.post(ME_URL).status_code, 403)
        self.assertEqual(client.post(ME_URL, HTTP_X_CSRFTOKEN=csrf_token(client)).status_code, 405)
