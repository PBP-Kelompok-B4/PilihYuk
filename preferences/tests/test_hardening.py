from django.core.cache import cache
from django.test import TestCase

from preferences.models import Preference
from .helpers import make_user


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
