"""Tes alur penuh lewat API saja, dengan login sungguhan seperti aplikasi Flutter (lib/api.dart)."""
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from .tests import make_complete_product

PASSWORD = "RahasiaUji123!"
API = "/api/v1/corrections/"
# Seperti di PWS: HTTPS, token dari cookie csrftoken di header X-CSRFToken, dan Referer.
HTTPS = {"secure": True, "HTTP_REFERER": "https://testserver/"}


def account(email, name, **extra):
    return get_user_model().objects.create_user(
        username=email, email=email, password=PASSWORD, first_name=name, **extra
    )


class AppSession:
    """Satu klien dengan sesi hasil POST /api/v1/auth/login/."""

    def __init__(self, test, email):
        self.test = test
        self.client = APIClient(enforce_csrf_checks=True)
        response = self.client.post("/api/v1/auth/login/", {"username": email, "password": PASSWORD}, **HTTPS)
        test.assertEqual(response.status_code, 200)
        self.token = response.cookies["csrftoken"].value

    def call(self, method, path, body=None, expected=200):
        response = getattr(self.client, method)(
            API + path, body, format="json", HTTP_X_CSRFTOKEN=self.token, **HTTPS
        )
        self.test.assertEqual(response.status_code, expected, response.content)
        return response.json() if response.content else None


class SubmitReviewWithdrawFlowTests(APITestCase):
    def test_submit_review_and_withdraw_only_through_api(self):
        account("pengaju@email.com", "Budi")
        account("kurator@email.com", "Kurator", is_staff=True)
        product = make_complete_product(fiber_100g=None, nova_group=None)
        public = APIClient()

        def queue_row():
            rows = public.get(API + "queue/").json()["results"]
            return next(row for row in rows if row["id"] == product.pk)

        self.assertEqual(queue_row()["status"], "needs_contribution")

        budi = AppSession(self, "pengaju@email.com")
        self.assertEqual(budi.call("get", "me/"), {"logged_in": True, "is_staff": False})
        body = {"product": product.pk, "items": [
            {"field_name": "fiber_100g", "proposed_value": "2,5"},
            {"field_name": "nova_group", "proposed_value": "3"},
        ]}
        correction = budi.call("post", "mine/", body, expected=201)
        self.assertEqual(budi.call("get", "mine/")["results"][0]["id"], correction["id"])
        self.assertEqual(queue_row()["status"], "needs_verification")

        curator = AppSession(self, "kurator@email.com")
        rows = curator.call("get", "moderation/")["results"]
        rows = {row["field_name"]: row for row in rows if row["correction_id"] == correction["id"]}
        self.assertEqual(sorted(rows), ["fiber_100g", "nova_group"])
        self.assertEqual(rows["fiber_100g"]["submitted_by"], "Budi")
        curator.call("patch", f"moderation/items/{rows['fiber_100g']['id']}/", {"status": "approved"})
        review = curator.call(
            "patch", f"moderation/items/{rows['nova_group']['id']}/",
            {"status": "rejected", "review_note": "Tidak sesuai label."},
        )
        self.assertEqual(review["correction"]["status"], "partial")

        detail = budi.call("get", f"mine/{correction['id']}/")
        self.assertEqual((detail["status"], detail["is_withdrawable"]), ("partial", False))
        notes = {item["field_name"]: (item["status"], item["review_note"]) for item in detail["items"]}
        expected = {"fiber_100g": ("approved", ""), "nova_group": ("rejected", "Tidak sesuai label.")}
        self.assertEqual(notes, expected)
        refused = budi.call("delete", f"mine/{correction['id']}/", expected=409)
        self.assertEqual(refused["code"], "not_withdrawable")

        product.refresh_from_db()
        self.assertEqual((product.fiber_100g, product.nova_group), (2.5, None))
        row = queue_row()
        self.assertEqual(row["status"], "needs_contribution")
        self.assertEqual([entry["key"] for entry in row["missing"]], ["nova"])