from django.core.cache import cache
from django.test import Client, TestCase
from unittest.mock import patch
import time

from preferences.models import Decision, Preference
from .helpers import make_product, make_user


class WriteRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = make_user()
        self.other = make_user("lain")
        self.item = Preference.objects.create(user=self.user, nutrient="protein", direction="max")
        self.client.force_login(self.user)

    def test_write_limit_is_per_user_and_leaves_reads_available(self):
        url = f"/preferensi/{self.item.pk}/ubah/"
        for _ in range(30):
            response = self.client.post(url, {"direction": "max", "weight": 2}, HTTP_ACCEPT="application/json")
            self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {"direction": "min", "weight": 3}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 429)
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.headers["Retry-After"], "60")
        self.assertEqual(self.client.get("/preferensi/", HTTP_ACCEPT="application/json").json()["items"][0]["direction"], "max")
        self.client.force_login(self.other)
        response = self.client.post("/preferensi/tambah/", {"nutrient": "fiber", "direction": "max", "weight": 2},
                                    HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 201)

    def test_limit_covers_all_write_endpoints_and_expires(self):
        product = make_product()
        decision = Decision.objects.create(user=self.user, product=product)
        urls = ["/preferensi/tambah/", "/preferensi/simpan/", f"/preferensi/{self.item.pk}/ubah/", f"/preferensi/{self.item.pk}/hapus/",
                "/keputusan/tambah/", f"/keputusan/{decision.pk}/ubah/", f"/keputusan/{decision.pk}/hapus/", "/keputusan/hapus-massal/"]
        for _ in range(30):
            self.client.post("/preferensi/tambah/", {})
        for url in urls:
            response = self.client.post(url, HTTP_ACCEPT="application/json")
            self.assertEqual(response.status_code, 429)
        self.assertContains(self.client.post("/keputusan/tambah/"), "Perubahan terlalu sering", status_code=429)
        future = time.time() + 61
        with patch("time.time", return_value=future):
            response = self.client.post(f"/preferensi/{self.item.pk}/ubah/", {"direction": "min", "weight": 3},
                                        HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)


class BulkDeleteTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = make_user()
        self.other = make_user("lain")
        product = make_product()
        self.first = Decision.objects.create(user=self.user, product=product)
        self.second = Decision.objects.create(user=self.user, product=product)
        self.foreign = Decision.objects.create(user=self.other, product=product)
        self.client.force_login(self.user)

    def test_delete_multiple_owned_decisions_and_preserve_foreign_history(self):
        response = self.client.post("/keputusan/hapus-massal/", {"ids": [self.first.pk, self.second.pk]},
                                    HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted_ids"], [self.first.pk, self.second.pk])
        self.assertEqual(self.client.get("/keputusan/", HTTP_ACCEPT="application/json").json()["items"], [])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get("/keputusan/", HTTP_ACCEPT="application/json").json()["items"][0]["id"], self.foreign.pk)

    def test_mixed_owner_or_missing_ids_never_partially_delete(self):
        for ids, code in (([self.first.pk, self.foreign.pk], 403), ([self.first.pk, 99999], 404)):
            for headers in ({}, {"HTTP_ACCEPT": "application/json"}):
                response = self.client.post("/keputusan/hapus-massal/", {"ids": ids}, **headers)
                self.assertEqual(response.status_code, code)
        items = self.client.get("/keputusan/", HTTP_ACCEPT="application/json").json()["items"]
        self.assertEqual({item["id"] for item in items}, {self.first.pk, self.second.pk})

    def test_validation_methods_login_and_csrf(self):
        for ids in ([], ["abc"], [0], [-1], ["999999999999999999999999999"], [self.first.pk] * 101):
            response = self.client.post("/keputusan/hapus-massal/", {"ids": ids}, HTTP_ACCEPT="application/json")
            self.assertEqual(response.status_code, 400)
            self.assertIn("ids", response.json()["errors"])
        self.assertEqual(self.client.post("/keputusan/hapus-massal/", {}).status_code, 400)
        self.assertEqual(self.client.get("/keputusan/hapus-massal/").status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post("/keputusan/hapus-massal/").status_code, 302)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/keputusan/hapus-massal/", {"ids": [self.first.pk]}).status_code, 403)
        client.get("/keputusan/")
        response = client.post("/keputusan/hapus-massal/", {"ids": [self.first.pk, self.first.pk]},
                               HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
        self.assertRedirects(response, "/keputusan/")
