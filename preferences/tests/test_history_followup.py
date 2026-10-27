from django.core.cache import cache
from django.test import TestCase

from preferences.models import Decision
from .helpers import make_product, make_shelf, make_user


class HistoryFollowupTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = make_user()
        self.product = make_product()
        self.client.force_login(self.user)

    def test_foreign_shelf_made_private_is_redacted_in_history(self):
        shelf = make_shelf(make_user("lain"), self.product, name="Nama privat rahasia", is_private=True)
        Decision.objects.create(user=self.user, product=self.product, shelf=shelf)
        response = self.client.get("/riwayat/", HTTP_ACCEPT="application/json")
        self.assertNotIn("Nama privat rahasia", response.content.decode())
        self.assertIsNone(response.json()["items"][0]["shelf_id"])
