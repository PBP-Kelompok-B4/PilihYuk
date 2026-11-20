"""Tes API DRF Modul 4: GET /api/v1/corrections/queue/ (antrean kontribusi, publik).

Helper data (make_product, make_shelf, dst.) dipakai ulang dari tests.py supaya datanya
dibuat dengan cara yang sama dengan tes halaman web.
"""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from product_catalog.models import Product

from .constants import PENDING
from .tests import (
    COMPLETE_FIELDS,
    OFF_IMAGE,
    make_complete_product,
    make_correction,
    make_shelf,
    make_user,
    shelves_unavailable,
)

URL = "/api/v1/corrections/queue/"

PAGE_KEYS = [
    "count", "page", "page_size", "num_pages", "next_page", "previous_page", "sort", "missing",
    "shelf_available", "sort_options", "missing_options", "stats", "results",
]
ROW_KEYS = [
    "id", "product_name", "brand", "quantity", "image_url", "missing", "missing_count",
    "shelf_count", "status", "status_label",
]
WEB_ONLY_KEYS = {"submit_url", "detail_url"}  # tautan halaman web, tidak dikirim ke aplikasi


class ContributionQueueApiTests(APITestCase):
    def setUp(self):
        # pbp_django_auth tidak mengirim token CSRF, jadi klien tes tetap memeriksanya.
        self.client = APIClient(enforce_csrf_checks=True)
        self.fiber = make_complete_product(product_name="Sarimi Isi 2 Goreng", fiber_100g=None, image_url=OFF_IMAGE)
        self.nova = make_complete_product(product_name="Teh Botol Sosro", nova_group=None, brand="")
        self.complete = make_complete_product(product_name="Indomie Goreng")

    def get(self, query=""):
        response = self.client.get(URL + query)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_url_is_stable(self):
        self.assertEqual(reverse("data_correction_api:contribution_queue"), URL)

    def test_public_without_login_and_json_shape(self):
        make_shelf(self.fiber)
        data = self.get()
        self.assertEqual(list(data), PAGE_KEYS)
        self.assertEqual(
            {key: data[key] for key in PAGE_KEYS[:9]},
            {"count": 2, "page": 1, "page_size": 20, "num_pages": 1, "next_page": None,
             "previous_page": None, "sort": "shelf", "missing": None, "shelf_available": True},
        )
        self.assertEqual(data["sort_options"], [
            {"key": "shelf", "label": "Paling sering di shelf"},
            {"key": "kosong", "label": "Paling banyak data kosong"},
            {"key": "terbaru", "label": "Terbaru"},
        ])
        self.assertEqual(data["missing_options"], [
            {"key": "nutrition", "label": "Gizi"}, {"key": "nova", "label": "NOVA"}, {"key": "brand", "label": "Merek"},
        ])
        self.assertEqual(data["stats"], {
            "incomplete_products": 2, "submitted_last_7_days": 0, "approved": 0, "shelf_average": 0.5,
        })
        first = data["results"][0]  # paling sering di shelf: Sarimi (1 shelf publik)
        self.assertEqual(list(first), ROW_KEYS)
        self.assertEqual(first, {
            "id": self.fiber.pk, "product_name": "Sarimi Isi 2 Goreng", "brand": "Sarimi", "quantity": "88 g",
            "image_url": OFF_IMAGE,
            "missing": [{"key": "nutrition", "label": "Gizi", "correctable": True, "fields": ["fiber_100g"]}],
            "missing_count": 1, "shelf_count": 1,
            "status": "needs_contribution", "status_label": "Perlu kontribusi",
        })
        self.assertEqual(data["results"][1]["image_url"], "")  # tanpa gambar: string kosong
        self.assertNotIn(self.complete.pk, [row["id"] for row in data["results"]])

    def test_same_rows_and_stats_as_web_json(self):
        make_shelf(self.nova)
        make_correction(self.fiber, make_user(), fiber_100g=PENDING)
        for query in ("", "?sort=kosong", "?sort=terbaru", "?missing=nova", "?sort=acak&missing=code&page=9"):
            with self.subTest(query=query):
                web = self.client.get("/antrean/" + query, HTTP_ACCEPT="application/json").json()
                api = self.get(query)
                web_rows = [{key: row[key] for key in row if key not in WEB_ONLY_KEYS} for row in web["results"]]
                api_rows = [{key: row[key] for key in row if key != "image_url"} for row in api["results"]]
                self.assertEqual(api_rows, web_rows)
                for key in ("count", "page", "page_size", "sort", "missing", "shelf_available", "stats"):
                    self.assertEqual(api[key], web[key], key)

    def test_filter_sort_and_page(self):
        extra = [make_complete_product(product_name=f"Produk {n:02d}", sugars_100g=None) for n in range(25)]
        newest = extra[10]
        Product.objects.filter(pk=newest.pk).update(created_at=timezone.now() + timedelta(days=1))
        self.assertEqual([row["id"] for row in self.get("?missing=nova")["results"]], [self.nova.pk])
        # Teh kurang 2 data (NOVA dan merek), yang lain kurang 1: Teh paling atas.
        self.assertEqual(self.get("?sort=kosong")["results"][0]["id"], self.nova.pk)
        self.assertEqual(self.get("?sort=terbaru")["results"][0]["id"], newest.pk)
        second = self.get("?sort=kosong&page=2")
        self.assertEqual(
            (second["count"], second["page"], second["num_pages"], second["next_page"], second["previous_page"]),
            (27, 2, 2, None, 1),
        )
        self.assertEqual(len(second["results"]), 7)
        self.assertEqual(self.get("?page=99")["page"], 2)  # lewat dari halaman terakhir -> terakhir

    def test_unknown_values_fall_back_to_defaults(self):
        data = self.get("?sort=acak&missing=code&page=abc")
        self.assertEqual((data["sort"], data["missing"], data["page"]), ("shelf", None, 1))
        self.assertEqual(data["count"], 2)

    def test_private_shelf_is_not_counted(self):
        make_shelf(self.fiber)
        make_shelf(self.fiber)
        make_shelf(self.fiber, self.nova, private=True)
        data = self.get()
        counts = {row["id"]: row["shelf_count"] for row in data["results"]}
        self.assertEqual(counts, {self.fiber.pk: 2, self.nova.pk: 0})
        self.assertEqual(data["stats"]["shelf_average"], 1.0)

    def test_without_shelf_data_falls_back_to_most_missing(self):
        with shelves_unavailable():
            data = self.get("?sort=shelf")
        self.assertEqual((data["sort"], data["shelf_available"]), ("kosong", False))
        self.assertEqual([option["key"] for option in data["sort_options"]], ["kosong", "terbaru"])
        self.assertEqual({row["shelf_count"] for row in data["results"]}, {None})
        self.assertIsNone(data["stats"]["shelf_average"])

    def test_pending_status_without_submitter_identity(self):
        rahasia = make_user("rahasia.pengaju@email.com", "Rahasiawati")
        make_correction(self.fiber, rahasia, fiber_100g=PENDING)
        response = self.client.get(URL)
        row = next(row for row in response.json()["results"] if row["id"] == self.fiber.pk)
        self.assertEqual((row["status"], row["status_label"]), ("needs_verification", "Perlu verifikasi"))
        self.assertEqual(response.json()["stats"]["submitted_last_7_days"], 1)
        for secret in ("rahasia.pengaju@email.com", "Rahasiawati", "submitted_by", "pengaju"):
            self.assertNotIn(secret, response.content.decode())

    def test_query_count_is_constant(self):
        self.assertNumQueries(6, self.client.get, URL)
        for n in range(30):
            product = make_complete_product(product_name=f"Tambahan {n}", origin="")
            make_shelf(product)
            make_correction(product, make_user(f"u{n}@email.com"), origin=PENDING)
        for query, queries in (("", 6), ("?missing=origin&page=2", 6), ("?sort=terbaru", 7)):
            with self.subTest(query=query), self.assertNumQueries(queries):
                self.assertEqual(self.client.get(URL + query).status_code, 200)

    def test_logged_in_user_gets_the_same_page(self):
        anonymous = self.get()
        self.client.force_login(make_user())
        self.assertEqual(self.get(), anonymous)

    def test_only_get_is_allowed(self):
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                self.assertEqual(getattr(self.client, method)(URL).status_code, 405)
        # Sudah login tapi tanpa token CSRF: ditolak lebih dulu oleh SessionAuthentication.
        self.client.force_login(make_user())
        self.assertEqual(self.client.post(URL).status_code, 403)

    def test_empty_queue(self):
        for product in (self.fiber, self.nova):
            for field, value in COMPLETE_FIELDS.items():
                setattr(product, field, value)
            product.save()
        data = self.get()
        self.assertEqual((data["count"], data["page"], data["num_pages"], data["results"]), (0, 1, 1, []))
        self.assertEqual(data["missing_options"], [])
        self.assertEqual(data["stats"]["shelf_average"], 0)

    def test_browsable_api_page(self):
        response = self.client.get(URL, HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])
        self.assertContains(response, "Sarimi Isi 2 Goreng")