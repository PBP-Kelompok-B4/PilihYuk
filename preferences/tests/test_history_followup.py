from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
import csv
import io

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

    def test_export_includes_all_filtered_rows_and_neutralizes_formulas(self):
        for index in range(12):
            Decision.objects.create(user=self.user, product=self.product, note="=1+1", compared_product_count=2)
        Decision.objects.create(user=make_user("lain"), product=self.product, note="Rahasia")
        response = self.client.get("/riwayat/ekspor/", {"q": "Produk", "page": 2})
        self.assertEqual(response.status_code, 200)
        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0]["note"], "'=1+1")
        self.assertEqual(rows[0]["compared_product_count"], "2")
        self.assertNotIn("Rahasia", response.content.decode())
        self.assertEqual(self.client.get("/riwayat/ekspor/", {"q": "tidak-cocok"}).content.decode("utf-8-sig").count("\n"), 1)

    def test_summary_uses_whole_history_and_month_filter_does_not_remove_null_rows(self):
        for index in range(12):
            Decision.objects.create(user=self.user, product=self.product)
        Decision.objects.create(user=self.user, product=None)
        response = self.client.get("/riwayat/", {"q": "tidak-cocok"})
        self.assertEqual(response.context["summary"]["total"], 13)
        self.assertEqual(response.context["summary"]["products"], 1)
        result = self.client.get("/riwayat/", {"bulan": "ini"}, HTTP_ACCEPT="application/json").json()
        self.assertEqual(result["total"], 13)
