"""Tes API moderasi: GET moderation/, moderation/guide/, dan moderation/items/<pk>/."""
import json

from django.urls import reverse
from rest_framework.test import APITestCase

from product_catalog.models import Product

from . import moderation
from .api_fixtures import api_client
from .constants import APPROVED, PENDING, REJECTED
from .models import DataCorrectionItem
from .permissions import AUTH_REQUIRED, FORBIDDEN
from .tests import make_complete_product, make_correction, make_staff, make_user, set_created_at, submit_items

QUEUE_URL = "/api/v1/corrections/moderation/"
GUIDE_URL = "/api/v1/corrections/moderation/guide/"
WEB_URL = "/moderasi/"
ROW_KEYS = [
    "id", "correction_id", "product", "submitted_by", "created_at", "field_name", "label",
    "old_value", "proposed_value", "current_value", "old_display", "proposed_display", "current_display",
    "status", "status_label", "review_note", "stale",
]
PAGE_KEYS = [
    "count", "page", "page_size", "num_pages", "next_page", "previous_page", "tab", "field", "status",
    "tab_options", "field_options", "status_options", "stats", "results",
]
ITEM_NOT_FOUND = {
    "detail": "Item tidak ditemukan atau pengajuannya sudah ditarik.",
    "code": "correction_not_found",
}


def item_url(pk):
    return reverse("data_correction_api:curator_item", args=[pk])


class ModerationApiTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_complete_product(fiber_100g=None)
        self.client = api_client(make_staff())

    def item(self, hours_ago, **statuses):
        """Satu pengajuan dengan item per field, dibuat hours_ago jam lalu; hasil: item pertama."""
        correction = make_correction(self.product, self.user, **statuses)
        item = correction.items.order_by("pk").first()
        set_created_at(item, hours=hours_ago)
        return item

    def get(self, query=""):
        response = self.client.get(QUEUE_URL + query)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def ids(self, query=""):
        return [row["id"] for row in self.get(query)["results"]]

    def test_urls_are_stable(self):
        self.assertEqual(reverse("data_correction_api:curator_queue"), QUEUE_URL)
        self.assertEqual(reverse("data_correction_api:field_guide"), GUIDE_URL)
        self.assertEqual(item_url(5), "/api/v1/corrections/moderation/items/5/")

    def test_visitor_and_regular_user_get_403(self):
        item = self.item(1, brand=PENDING)
        for client, body in ((api_client(), AUTH_REQUIRED), (api_client(self.user), FORBIDDEN)):
            for url in (QUEUE_URL, GUIDE_URL, item_url(item.pk)):
                with self.subTest(url=url, body=body["code"]):
                    response = client.get(url)
                    self.assertEqual((response.status_code, response.json()), (403, body))

    def test_antrean_tab_only_pending_oldest_first(self):
        newer = self.item(1, brand=PENDING)
        older = self.item(3, brand=PENDING)
        self.item(2, brand=APPROVED)
        data = self.get()
        self.assertEqual(list(data), PAGE_KEYS)
        self.assertEqual((data["tab"], data["field"], data["status"]), ("antrean", None, None))
        self.assertEqual([row["id"] for row in data["results"]], [older.pk, newer.pk])
        self.assertEqual(list(data["results"][0]), ROW_KEYS)

    def test_semua_tab_status_filter_newest_first(self):
        older = self.item(3, brand=REJECTED)
        newer = self.item(1, brand=REJECTED)
        approved = self.item(2, brand=APPROVED)
        pending = self.item(4, brand=PENDING)
        self.assertEqual(self.ids("?tab=semua"), [newer.pk, approved.pk, older.pk, pending.pk])
        data = self.get("?tab=semua&status=rejected")
        self.assertEqual((data["tab"], data["status"]), ("semua", "rejected"))
        self.assertEqual([row["id"] for row in data["results"]], [newer.pk, older.pk])

    def test_field_filter(self):
        fiber = self.item(2, fiber_100g=PENDING)
        self.item(1, brand=PENDING)
        data = self.get("?field=fiber_100g")
        self.assertEqual((data["field"], [row["id"] for row in data["results"]]), ("fiber_100g", [fiber.pk]))

    def test_unknown_values_fall_back_to_default(self):
        pending = self.item(2, brand=PENDING)
        self.item(1, brand=REJECTED)
        for query in ("?tab=riwayat&field=code&status=rejected", "?tab=panduan", "?status=rejected"):
            with self.subTest(query=query):
                data = self.get(query)
                self.assertEqual((data["tab"], data["field"], data["status"]), ("antrean", None, None))
                self.assertEqual([row["id"] for row in data["results"]], [pending.pk])

    def test_stats_and_options(self):
        self.item(3, brand=PENDING, fiber_100g=APPROVED)
        self.item(2, brand=REJECTED)
        data = self.get()
        self.assertEqual(data["stats"], moderation.queue_stats())
        self.assertEqual(data["stats"], {"pending": 1, "approved": 1, "rejected": 1})
        self.assertEqual([option["key"] for option in data["tab_options"]], ["antrean", "semua", "panduan"])
        self.assertEqual(len(data["field_options"]), 14)
        self.assertIn({"key": "fiber_100g", "label": "Serat (g/100 g)"}, data["field_options"])
        self.assertEqual(data["status_options"], [])
        keys = [option["key"] for option in self.get("?tab=semua")["status_options"]]
        self.assertEqual(keys, ["pending", "approved", "rejected"])

    def test_guide_lists_14_fields(self):
        response = self.client.get(GUIDE_URL)
        self.assertEqual(response.status_code, 200)
        fields = response.json()["fields"]
        self.assertEqual(len(fields), 14)
        self.assertEqual(fields, json.loads(json.dumps(moderation.field_guide())))
        self.assertEqual(list(fields[0]), ["field_name", "label", "kind", "rules"])

    def test_pagination_twenty_per_page(self):
        items = [self.item(30 - number, brand=PENDING) for number in range(25)]
        first = self.get()
        self.assertEqual(
            {key: first[key] for key in PAGE_KEYS[:6]},
            {"count": 25, "page": 1, "page_size": 20, "num_pages": 2, "next_page": 2, "previous_page": None},
        )
        self.assertEqual(self.ids("?page=2"), [item.pk for item in items[20:]])
        self.assertEqual(self.ids("?page=abc"), [item.pk for item in items[:20]])

    def test_current_value_and_stale_after_product_changes(self):
        items = submit_items(self.product, self.user, fiber_100g="2,5", sodium_100g="500")
        row = self.client.get(item_url(items["fiber_100g"].pk)).json()
        self.assertEqual(
            {key: row[key] for key in ("old_value", "proposed_value", "current_value", "stale")},
            {"old_value": None, "proposed_value": 2.5, "current_value": None, "stale": False},
        )
        Product.objects.filter(pk=self.product.pk).update(fiber_100g=1.2, sodium_100g=0.3)
        row = self.client.get(item_url(items["fiber_100g"].pk)).json()
        self.assertEqual((row["current_value"], row["current_display"], row["stale"]), (1.2, "1,2", True))
        sodium = self.client.get(item_url(items["sodium_100g"].pk)).json()
        self.assertEqual(
            [sodium[key] for key in ("old_display", "proposed_value", "proposed_display", "current_display")],
            ["780", 0.5, "500", "300"],
        )
        DataCorrectionItem.objects.filter(pk=items["fiber_100g"].pk).update(status=APPROVED)
        self.assertFalse(self.client.get(item_url(items["fiber_100g"].pk)).json()["stale"])

    def test_submitter_is_display_name_only(self):
        secret = make_user("rahasia.pengaju@email.com", "Rahasiawati")
        item = make_correction(self.product, secret, brand=PENDING).items.get()
        for url in (QUEUE_URL, QUEUE_URL + "?tab=semua", item_url(item.pk)):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn('"submitted_by":"Rahasiawati"', response.content.decode())
                self.assertNotIn("rahasia.pengaju@email.com", response.content.decode())

    def test_item_detail_reviewed_and_missing(self):
        pending = self.item(2, brand=PENDING)
        rejected = self.item(1, brand=REJECTED)
        self.assertEqual(self.client.get(item_url(pending.pk)).json(), self.get()["results"][0])
        row = self.client.get(item_url(rejected.pk)).json()
        row = {key: row[key] for key in ("id", "status", "status_label")}
        self.assertEqual(row, {"id": rejected.pk, "status": "rejected", "status_label": "Ditolak"})
        withdrawn = self.item(1, brand=PENDING)
        withdrawn.correction.delete()
        for pk in (withdrawn.pk, 999999):
            with self.subTest(pk=pk):
                response = self.client.get(item_url(pk))
                self.assertEqual((response.status_code, response.json()), (404, ITEM_NOT_FOUND))

    def test_query_count_does_not_grow_with_items(self):
        self.item(1, brand=PENDING)
        with self.assertNumQueries(5):  # sesi, user, count, halaman + produk + pengaju, stats
            self.get()
        for number in range(24):
            self.item(2 + number, fiber_100g=PENDING)
        with self.assertNumQueries(5):
            self.get()
        with self.assertNumQueries(5):
            self.get("?tab=semua&field=fiber_100g")

    def test_same_rows_as_web_page(self):
        self.item(3, brand=PENDING, fiber_100g=APPROVED)
        self.item(2, brand=REJECTED)
        for number in range(22):
            self.item(4 + number, fiber_100g=PENDING)
        queries = ("", "?page=2", "?tab=semua", "?tab=semua&status=rejected", "?field=fiber_100g", "?tab=x")
        for query in queries:
            with self.subTest(query=query):
                web = self.client.get(WEB_URL + query, HTTP_ACCEPT="application/json").json()
                api = self.get(query)
                for key in ("count", "page", "page_size", "tab", "field", "status", "stats"):
                    self.assertEqual(api[key], web[key], key)
                self.assertEqual(len(api["results"]), len(web["results"]))
                for api_row, web_row in zip(api["results"], web["results"]):
                    keys = [key for key in web_row if key not in ("product", "created_at")]
                    self.assertEqual({key: api_row[key] for key in keys}, {key: web_row[key] for key in keys})
                    product = web_row["product"]
                    self.assertEqual({key: api_row["product"][key] for key in product}, product)