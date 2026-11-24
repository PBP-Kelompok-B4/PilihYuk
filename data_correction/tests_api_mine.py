"""Tes API GET mine/ dan GET mine/<pk>/."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .api_fixtures import api_client, csrf_token
from .constants import APPROVED, PENDING, REJECTED
from .models import DataCorrection
from .tests import make_complete_product, make_correction, make_user
from .tests_api_submit import CORRECTION_KEYS, ITEM_KEYS, PRODUCT_KEYS

MINE_URL = "/api/v1/corrections/mine/"
WEB_URL = "/antrean/saya/"
PAGE_KEYS = ["count", "page", "page_size", "num_pages", "next_page", "previous_page", "results"]
NOT_FOUND = {"detail": "Pengajuan tidak ditemukan.", "code": "correction_not_found"}
SHARED_KEYS = ["id", "status", "status_label", "is_withdrawable"]
SHARED_ITEM_KEYS = [
    "field_name", "label", "old_value", "proposed_value", "status", "status_label", "review_note",
]


def detail_url(pk):
    return reverse("data_correction_api:correction_detail", args=[pk])


class MyCorrectionsApiTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("lain@email.com", "Lain")
        self.product = make_complete_product(product_name="Sarimi Isi 2 Goreng", fiber_100g=None)
        self.client = api_client(self.user)

    def list_ids(self, query=""):
        response = self.client.get(MINE_URL + query)
        self.assertEqual(response.status_code, 200)
        return [row["id"] for row in response.json()["results"]]

    def make_many(self, count, user=None):
        return [make_correction(self.product, user or self.user, brand=PENDING) for _ in range(count)]

    def test_urls_are_stable(self):
        self.assertEqual(reverse("data_correction_api:my_corrections"), MINE_URL)
        self.assertEqual(detail_url(5), "/api/v1/corrections/mine/5/")

    def test_visitor_gets_403(self):
        correction = make_correction(self.product, self.user, brand=PENDING)
        visitor = api_client()
        self.assertEqual(visitor.get(MINE_URL).status_code, 403)
        self.assertEqual(visitor.get(detail_url(correction.pk)).status_code, 403)

    def test_list_shows_only_own_corrections_newest_first(self):
        older = make_correction(self.product, self.user, brand=PENDING)
        make_correction(self.product, self.other, brand=PENDING)
        newer = make_correction(self.product, self.user, fiber_100g=PENDING)
        DataCorrection.objects.filter(pk=older.pk).update(created_at=timezone.now() - timedelta(hours=1))

        data = self.client.get(MINE_URL).json()
        self.assertEqual(list(data), PAGE_KEYS)
        self.assertEqual((data["count"], [row["id"] for row in data["results"]]), (2, [newer.pk, older.pk]))
        first = data["results"][0]
        self.assertEqual(list(first), CORRECTION_KEYS)
        self.assertEqual(list(first["product"]), PRODUCT_KEYS)
        self.assertEqual(list(first["items"][0]), ITEM_KEYS)

    def test_empty_list(self):
        data = self.client.get(MINE_URL).json()
        self.assertEqual(data, {
            "count": 0, "page": 1, "page_size": 10, "num_pages": 1, "next_page": None,
            "previous_page": None, "results": [],
        })

    def test_pagination_ten_per_page(self):
        corrections = self.make_many(12)
        newest_first = [correction.pk for correction in reversed(corrections)]
        first = self.client.get(MINE_URL).json()
        self.assertEqual(
            {key: first[key] for key in PAGE_KEYS[:6]},
            {"count": 12, "page": 1, "page_size": 10, "num_pages": 2, "next_page": 2, "previous_page": None},
        )
        self.assertEqual([row["id"] for row in first["results"]], newest_first[:10])
        second = self.client.get(MINE_URL + "?page=2").json()
        self.assertEqual((second["page"], second["next_page"], second["previous_page"]), (2, None, 1))
        self.assertEqual([row["id"] for row in second["results"]], newest_first[10:])
        self.assertEqual(self.list_ids("?page=abc"), newest_first[:10])
        self.assertEqual(self.list_ids("?page=99"), newest_first[10:])

    def test_same_order_pages_and_values_as_web_page(self):
        self.make_many(11)
        make_correction(self.product, self.user, brand=APPROVED, fiber_100g=REJECTED)
        self.make_many(2, self.other)
        for query in ("", "?page=2", "?page=abc", "?page=99"):
            with self.subTest(query=query):
                web = self.client.get(WEB_URL + query, HTTP_ACCEPT="application/json").json()
                api = self.client.get(MINE_URL + query).json()
                for key in ("count", "page", "page_size"):
                    self.assertEqual(api[key], web[key], key)
                self.assertEqual(len(api["results"]), len(web["results"]))
                for api_row, web_row in zip(api["results"], web["results"]):
                    self.assertEqual(
                        {key: api_row[key] for key in SHARED_KEYS}, {key: web_row[key] for key in SHARED_KEYS}
                    )
                    self.assertEqual(
                        {key: api_row["product"][key] for key in ("id", "product_name")}, web_row["product"]
                    )
                    self.assertEqual(
                        [{key: item[key] for key in SHARED_ITEM_KEYS} for item in api_row["items"]],
                        web_row["items"],
                    )

    def test_detail_returns_own_correction(self):
        correction = make_correction(self.product, self.user, brand=PENDING, fiber_100g=PENDING)
        response = self.client.get(detail_url(correction.pk))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, self.client.get(MINE_URL).json()["results"][0])
        self.assertEqual(data["product"]["id"], self.product.pk)
        self.assertEqual([item["field_name"] for item in data["items"]], ["brand", "fiber_100g"])

    def test_detail_of_someone_else_or_missing_is_404(self):
        theirs = make_correction(self.product, self.other, brand=PENDING)
        for pk in (theirs.pk, 999999):
            with self.subTest(pk=pk):
                response = self.client.get(detail_url(pk))
                self.assertEqual((response.status_code, response.json()), (404, NOT_FOUND))

    def test_derived_status_and_withdrawable(self):
        cases = [
            ({"brand": PENDING}, "pending", "Menunggu", True),
            ({"brand": APPROVED}, "approved", "Disetujui", False),
            ({"brand": REJECTED}, "rejected", "Ditolak", False),
            ({"brand": APPROVED, "fiber_100g": REJECTED}, "partial", "Sebagian disetujui", False),
            ({"brand": PENDING, "fiber_100g": APPROVED}, "pending", "Menunggu", False),
        ]
        for statuses, status, label, withdrawable in cases:
            with self.subTest(statuses=statuses):
                correction = make_correction(self.product, self.user, **statuses)
                data = self.client.get(detail_url(correction.pk)).json()
                self.assertEqual((data["status"], data["status_label"], data["is_withdrawable"]),
                                 (status, label, withdrawable))
                self.assertEqual({item["field_name"]: item["status"] for item in data["items"]}, statuses)

    def test_query_count_does_not_grow_with_corrections(self):
        make_correction(self.product, self.user, brand=PENDING, fiber_100g=PENDING)
        with self.assertNumQueries(5):  # sesi, user, count, pengajuan+produk, item
            self.assertEqual(self.client.get(MINE_URL).status_code, 200)
        for _ in range(11):
            make_correction(self.product, self.user, brand=APPROVED, fiber_100g=PENDING)
        with self.assertNumQueries(5):
            self.assertEqual(self.client.get(MINE_URL).status_code, 200)
        url = detail_url(DataCorrection.objects.first().pk)
        with self.assertNumQueries(4):
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_no_submitter_identity_in_responses(self):
        secret = make_user("rahasia.pengaju@email.com", "Rahasiawati")
        client = api_client(secret)
        correction = make_correction(self.product, secret, brand=PENDING)
        for url in (MINE_URL, detail_url(correction.pk)):
            with self.subTest(url=url):
                content = client.get(url).content.decode()
                for text in ("rahasia.pengaju@email.com", "Rahasiawati", "submitted_by", "reviewed_by"):
                    self.assertNotIn(text, content)

    def test_list_only_allows_get_and_post(self):
        token = csrf_token(self.client)
        for method in ("put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(MINE_URL, {}, format="json", HTTP_X_CSRFTOKEN=token)
                self.assertEqual(response.status_code, 405)