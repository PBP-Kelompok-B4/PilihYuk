from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

from django.test import Client, TestCase

from preferences.models import Decision
from .helpers import make_product, make_shelf, make_user


class DecisionViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product()
        self.shelf = make_shelf(self.user, self.product)

    def test_comparison_contract_creates_and_lists_private_decision(self):
        self.client.force_login(self.user)
        response = self.client.post("/riwayat/tambah/", {
            "product": self.product.pk, "shelf": self.shelf.pk, "note": "Pilihan hari ini",
        }, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 201)
        item = response.json()["item"]
        self.assertEqual((item["product_name"], item["shelf_name"], item["note"]),
                         ("Produk contoh", "Shelf contoh", "Pilihan hari ini"))
        self.assertContains(self.client.get("/riwayat/"), "Pilihan hari ini")

    def test_html_crud_and_invalid_input(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post("/riwayat/tambah/", {"product": self.product.pk}), "/riwayat/")
        item = self.client.get("/riwayat/", HTTP_ACCEPT="application/json").json()["items"][0]
        url = f"/riwayat/{item['id']}/ubah/"
        self.assertRedirects(self.client.post(url, {"note": "Catatan baru"}), "/riwayat/")
        self.assertContains(self.client.get("/riwayat/"), "Catatan baru")
        self.assertEqual(self.client.post(url, {"note": "x" * 501}).status_code, 400)
        self.assertEqual(self.client.post("/riwayat/tambah/", {}).status_code, 400)
        invalid = self.client.post("/riwayat/tambah/", {}, HTTP_ACCEPT="application/json")
        self.assertIn("product", invalid.json()["errors"])
        self.assertRedirects(self.client.post(f"/riwayat/{item['id']}/hapus/"), "/riwayat/")
        self.assertEqual(self.client.get("/riwayat/", HTTP_ACCEPT="application/json").json()["items"], [])

    def test_decision_ownership_guests_and_methods(self):
        decision = Decision.objects.create(user=self.user, product=self.product)
        other = make_user("lain")
        urls = ["/riwayat/", "/riwayat/tambah/", f"/riwayat/{decision.pk}/ubah/", f"/riwayat/{decision.pk}/hapus/"]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(other)
        self.assertEqual(self.client.get("/riwayat/", HTTP_ACCEPT="application/json").json()["items"], [])
        for url in urls[2:]:
            self.assertEqual(self.client.post(url).status_code, 403)
            self.assertEqual(self.client.post(url, HTTP_ACCEPT="application/json").status_code, 403)
        self.client.force_login(self.user)
        for url in urls[1:]:
            self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post("/riwayat/").status_code, 405)
        self.assertEqual(self.client.post("/riwayat/99999/hapus/", HTTP_ACCEPT="application/json").status_code, 404)

    def test_deleted_relations_render_and_note_remains_editable(self):
        decision = Decision.objects.create(user=self.user, product=self.product, shelf=self.shelf)
        self.shelf.delete()
        self.product.delete()
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/riwayat/"), "Tidak diketahui")
        result = self.client.post(f"/riwayat/{decision.pk}/ubah/", {"note": "Tetap tercatat"}, HTTP_ACCEPT="application/json")
        self.assertTrue(result.json()["ok"])
        self.assertIsNone(result.json()["item"]["product_id"])
        self.assertIsNone(result.json()["item"]["shelf_id"])
        self.assertEqual(self.client.post(f"/riwayat/{decision.pk}/hapus/", HTTP_ACCEPT="application/json").status_code, 200)

    def test_filter_search_and_pagination_json(self):
        self.client.force_login(self.user)
        for index in range(12):
            Decision.objects.create(user=self.user, product=self.product, shelf=self.shelf, note=str(index))
        other_product = make_product(product_name="Pilihan lain", brand="Merek lain")
        Decision.objects.create(user=self.user, product=other_product)
        response = self.client.get("/riwayat/", {"q": "MEREK LAIN"}, HTTP_ACCEPT="application/json")
        self.assertEqual(len(response.json()["items"]), 1)
        self.assertEqual(response.json()["items"][0]["product_name"], "Pilihan lain")
        response = self.client.get("/riwayat/", {"shelf": self.shelf.pk, "page": 2}, HTTP_ACCEPT="application/json")
        self.assertEqual(len(response.json()["items"]), 2)
        self.assertEqual(response.json()["page"], 2)
        self.assertIn("html", response.json())

    def test_date_boundaries_invalid_dates_and_query_links(self):
        self.client.force_login(self.user)
        for day in (1, 2, 3):
            item = Decision.objects.create(user=self.user, product=self.product, shelf=self.shelf)
            Decision.objects.filter(pk=item.pk).update(created_at=datetime(2026, 10, day, 12, tzinfo=timezone.utc))
        result = self.client.get("/riwayat/", {"dari": "2026-10-02", "sampai": "2026-10-02"},
                                 HTTP_ACCEPT="application/json").json()
        self.assertEqual(result["total"], 1)
        self.assertTrue(result["items"][0]["created_at"].startswith("2026-10-02"))
        result = self.client.get("/riwayat/", {"dari": "2026-02-30", "sampai": "bukan-tanggal"},
                                 HTTP_ACCEPT="application/json").json()
        self.assertEqual(result["total"], 3)
        self.assertEqual(len(result["notices"]), 2)
        self.assertIn("diabaikan", result["html"])
        for index in range(10):
            Decision.objects.create(user=self.user, product=self.product, shelf=self.shelf)
        params = {"q": "Produk", "shelf": str(self.shelf.pk), "dari": "2026-10-01"}
        response = self.client.get("/riwayat/", params)
        next_params = parse_qs(urlsplit(response.context["next_url"]).query)
        self.assertEqual(next_params, {"q": ["Produk"], "shelf": [str(self.shelf.pk)], "dari": ["2026-10-01"], "page": ["2"]})
        self.assertEqual(self.client.get("/riwayat/", {"page": "tidak-valid"}, HTTP_ACCEPT="application/json").json()["page"], 1)
        self.assertEqual(self.client.get("/riwayat/", {"page": 999}, HTTP_ACCEPT="application/json").json()["page"], 2)

    def test_filters_never_return_another_users_history_or_inactive_product_search(self):
        other = make_user("lain")
        Decision.objects.create(user=other, product=self.product, shelf=self.shelf, note="Rahasia")
        inactive = make_product(product_name="Produk lama", is_active=False)
        Decision.objects.create(user=self.user, product=inactive)
        self.client.force_login(self.user)
        result = self.client.get("/riwayat/", {"q": "Produk"}, HTTP_ACCEPT="application/json").json()
        self.assertEqual(result["items"], [])
        self.assertNotIn("Rahasia", result["html"])
        result = self.client.get("/riwayat/", {"shelf": self.shelf.pk}, HTTP_ACCEPT="application/json").json()
        self.assertEqual(result["total"], 0)

    def test_ajax_write_requires_csrf_and_returns_refreshed_list_fragment(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/riwayat/tambah/", {"product": self.product.pk}).status_code, 403)
        client.get("/riwayat/")
        headers = {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value, "HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
        response = client.post("/riwayat/tambah/", {"product": self.product.pk, "note": "Ditambahkan lewat AJAX"}, **headers)
        self.assertEqual(response.status_code, 201)
        item = response.json()["item"]
        result = client.get("/riwayat/", **headers).json()
        self.assertIn("Ditambahkan lewat AJAX", result["html"])
        self.assertEqual(client.post(f"/riwayat/{item['id']}/ubah/", {"note": "Diubah"}, **headers).status_code, 200)
        self.assertEqual(client.post(f"/riwayat/{item['id']}/hapus/", **headers).status_code, 200)
        self.assertEqual(client.get("/riwayat/", **headers).json()["total"], 0)
