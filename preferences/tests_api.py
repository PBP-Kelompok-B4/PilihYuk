from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from .constants import NUTRIENT_FIELDS, WRITE_LIMIT, WRITE_WINDOW_SECONDS
from .models import Decision, Preference
from .tests.helpers import make_product, make_shelf, make_user


class PreferencesAPITest(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("lain")
        self.product = make_product(proteins_100g=10)
        self.preference = Preference.objects.create(user=self.user, nutrient="protein", direction="max")
        self.decision = Decision.objects.create(user=self.user, product=self.product, note="Awal")
        key = f"preferences:writes:{self.user.pk}"
        cache.delete(key)
        self.addCleanup(cache.delete, key)
        self.client.force_login(self.user)
        self.preferences = reverse("preferences_api:preference-list")
        self.decisions = reverse("preferences_api:decision-list")

    def detail(self, resource, item):
        return reverse(f"preferences_api:{resource}-detail", args=[item.pk])

    def test_lists_only_return_current_users_data(self):
        Preference.objects.create(user=self.other, nutrient="fiber", direction="max")
        Decision.objects.create(user=self.other, product=self.product)
        for url, item in [(self.preferences, self.preference), (self.decisions, self.decision)]:
            self.assertEqual([row["id"] for row in self.client.get(url).json()], [item.pk])
            self.assertNotIn("user", self.client.get(url).json()[0])
        self.client.logout()
        for url in [self.preferences, self.decisions]:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_preference_crud_and_validation(self):
        payload = {"nutrient": "fiber", "direction": "max", "weight": 3, "user": self.other.pk}
        response = self.client.post(self.preferences, payload, format="json")
        self.assertEqual(response.status_code, 201)
        item = Preference.objects.get(pk=response.json()["id"])
        self.assertEqual(item.user, self.user)
        self.assertEqual(self.client.post(self.preferences, payload, format="json").status_code, 400)
        url = self.detail("preference", item)
        self.assertEqual(self.client.get(url).json()["weight"], 3)
        self.assertEqual(self.client.patch(url, {"weight": 4}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"nutrient": "sugar"}, format="json").status_code, 400)
        self.assertEqual(self.client.put(url, {"direction": "min", "weight": 1}, format="json").status_code, 200)
        item.refresh_from_db()
        self.assertEqual((item.nutrient, item.direction, item.weight), ("fiber", "min", 1))
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_foreign_objects_are_forbidden(self):
        self.client.force_login(self.other)
        for resource, item in [("preference", self.preference), ("decision", self.decision)]:
            url = self.detail(resource, item)
            for method in ("get", "patch", "delete"):
                self.assertEqual(getattr(self.client, method)(url).status_code, 403)
            self.assertTrue(type(item).objects.filter(pk=item.pk).exists())

    def test_decision_crud_preserves_snapshot(self):
        shelf = make_shelf(self.user, self.product)
        payload = {"product_id": self.product.pk, "shelf_id": shelf.pk,
                   "compared_product_ids": [self.product.pk], "note": "Pilihan"}
        response = self.client.post(self.decisions, payload, format="json")
        self.assertEqual(response.status_code, 201)
        item = Decision.objects.get(pk=response.json()["id"])
        self.assertEqual(item.compared_product_count, 1)
        url = self.detail("decision", item)
        self.assertEqual(self.client.get(url).json()["product_name"], self.product.product_name)
        self.assertEqual(self.client.patch(url, {"product_id": None}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"note": "Baru"}, format="json").status_code, 200)
        item.refresh_from_db()
        self.assertEqual((item.note, item.product_id), ("Baru", self.product.pk))
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_decision_rejects_private_shelf_and_hides_unavailable_relations(self):
        shelf = make_shelf(self.other, self.product, is_private=True)
        response = self.client.post(self.decisions, {"product_id": self.product.pk, "shelf_id": shelf.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.decision.shelf = shelf
        self.decision.save(update_fields=["shelf"])
        self.product.is_active = False
        self.product.save(update_fields=["is_active"])
        data = self.client.get(self.detail("decision", self.decision)).json()
        self.assertIsNone(data["shelf_id"])
        self.assertIsNone(data["product_id"])

    def test_previews_ignore_inactive_products_and_do_not_save(self):
        make_product(proteins_100g=100, is_active=False)
        url = reverse("preferences_api:preference-preview")
        self.assertEqual(self.client.get(url, {"nutrient": "invalid", "direction": "max"}).status_code, 400)
        result = self.client.get(url, {"nutrient": "protein", "direction": "max"}).json()
        self.assertEqual(result["samples"][0]["value"], 10)
        rows = [{"nutrient": key, "active": key == "protein", "direction": "max", "weight": 2}
                for key in NUTRIENT_FIELDS]
        url = reverse("preferences_api:preference-combined-preview")
        self.assertEqual(self.client.post(url, rows, format="json").status_code, 400)
        result = self.client.post(url, {"preferences": rows}, format="json")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["samples"][0]["id"], self.product.pk)
        self.assertEqual(Preference.objects.count(), 1)

    def test_bulk_delete_is_atomic_for_foreign_ids(self):
        foreign = Decision.objects.create(user=self.other, product=self.product)
        url = reverse("preferences_api:decision-bulk-delete")
        self.assertEqual(self.client.post(url, {"ids": []}, format="json").status_code, 400)
        payload = {"ids": [self.decision.pk, foreign.pk]}
        self.assertEqual(self.client.post(url, payload, format="json").status_code, 404)
        self.assertEqual(Decision.objects.count(), 2)
        response = self.client.post(url, {"ids": [self.decision.pk]}, format="json")
        self.assertEqual(response.json()["deleted_ids"], [self.decision.pk])
        self.assertTrue(Decision.objects.filter(pk=foreign.pk).exists())

    def test_api_writes_share_the_web_rate_limit(self):
        cache.set(f"preferences:writes:{self.user.pk}", WRITE_LIMIT, timeout=WRITE_WINDOW_SECONDS)
        response = self.client.post(self.preferences, {"nutrient": "fiber", "direction": "max"}, format="json")
        self.assertEqual(response.status_code, 429)
        self.assertFalse(Preference.objects.filter(user=self.user, nutrient="fiber").exists())
        self.assertEqual(self.client.get(self.preferences).status_code, 200)

    def test_session_writes_require_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        payload = {"nutrient": "fiber", "direction": "max"}
        self.assertEqual(client.post(self.preferences, payload, format="json").status_code, 403)
        client.get(reverse("preferences:preference_list"))
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(self.preferences, payload, format="json", HTTP_X_CSRFTOKEN=token).status_code, 201)
