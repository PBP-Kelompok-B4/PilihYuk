from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

from django.test import Client, TestCase
from django.core.cache import cache

from preferences.models import Decision
from .helpers import make_product, make_shelf, make_user


class DecisionViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = make_user()
        self.product = make_product()
        self.shelf = make_shelf(self.user, self.product)

    def test_comparison_contract_creates_and_lists_private_decision(self):
        self.client.force_login(self.user)
        response = self.client.post("/keputusan/tambah/", {
            "product": self.product.pk, "shelf": self.shelf.pk, "note": "Pilihan hari ini",
        }, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 201)
        item = response.json()["item"]
        self.assertEqual((item["product_name"], item["shelf_name"], item["note"]),
                         ("Produk contoh", "Shelf contoh", "Pilihan hari ini"))
        self.assertContains(self.client.get("/keputusan/"), "Pilihan hari ini")

    def test_html_crud_and_invalid_input(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post("/keputusan/tambah/", {"product": self.product.pk}), "/keputusan/")
        item = self.client.get("/keputusan/", HTTP_ACCEPT="application/json").json()["items"][0]
        url = f"/keputusan/{item['id']}/ubah/"
        self.assertRedirects(self.client.post(url, {"note": "Catatan baru"}), "/keputusan/")
        self.assertContains(self.client.get("/keputusan/"), "Catatan baru")
        self.assertEqual(self.client.post(url, {"note": "x" * 501}).status_code, 400)
        self.assertEqual(self.client.post("/keputusan/tambah/", {}).status_code, 400)
        invalid = self.client.post("/keputusan/tambah/", {}, HTTP_ACCEPT="application/json")
        self.assertIn("product", invalid.json()["errors"])
        self.assertRedirects(self.client.post(f"/keputusan/{item['id']}/hapus/"), "/keputusan/")
        self.assertEqual(self.client.get("/keputusan/", HTTP_ACCEPT="application/json").json()["items"], [])

    def test_decision_ownership_guests_and_methods(self):
        decision = Decision.objects.create(user=self.user, product=self.product)
        other = make_user("lain")
        urls = ["/keputusan/", "/keputusan/tambah/", f"/keputusan/{decision.pk}/ubah/", f"/keputusan/{decision.pk}/hapus/"]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(other)
        self.assertEqual(self.client.get("/keputusan/", HTTP_ACCEPT="application/json").json()["items"], [])
        for url in urls[2:]:
            self.assertEqual(self.client.post(url).status_code, 403)
            self.assertEqual(self.client.post(url, HTTP_ACCEPT="application/json").status_code, 403)
        self.client.force_login(self.user)
        for url in urls[1:]:
            self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post("/keputusan/").status_code, 405)
        self.assertEqual(self.client.post("/keputusan/99999/hapus/", HTTP_ACCEPT="application/json").status_code, 404)

    def test_deleted_relations_render_and_note_remains_editable(self):
        decision = Decision.objects.create(user=self.user, product=self.product, shelf=self.shelf)
        self.shelf.delete()
        self.product.delete()
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/keputusan/"), "Tidak diketahui")
        result = self.client.post(f"/keputusan/{decision.pk}/ubah/", {"note": "Tetap tercatat"}, HTTP_ACCEPT="application/json")
        self.assertTrue(result.json()["ok"])
        self.assertIsNone(result.json()["item"]["product_id"])
        self.assertIsNone(result.json()["item"]["shelf_id"])
        self.assertEqual(self.client.post(f"/keputusan/{decision.pk}/hapus/", HTTP_ACCEPT="application/json").status_code, 200)

    def test_filter_search_and_pagination_json(self):
        self.client.force_login(self.user)
        for index in range(12):
            Decision.objects.create(user=self.user, product=self.product, shelf=self.shelf, note=str(index))
        other_product = make_product(product_name="Pilihan lain", brand="Merek lain")
        Decision.objects.create(user=self.user, product=other_product)
        response = self.client.get("/keputusan/", {"q": "MEREK LAIN"}, HTTP_ACCEPT="application/json")
        self.assertEqual(len(response.json()["items"]), 1)
        self.assertEqual(response.json()["items"][0]["product_name"], "Pilihan lain")
        response = self.client.get("/keputusan/", {"shelf": self.shelf.pk, "page": 2}, HTTP_ACCEPT="application/json")
        self.assertEqual(len(response.json()["items"]), 2)
        self.assertEqual(response.json()["page"], 2)
        self.assertIn("html", response.json())

    def test_date_boundaries_invalid_dates_and_query_links(self):
        self.client.force_login(self.user)
        for day in (1, 2, 3):
            item = Decision.objects.create(user=self.user, product=self.product, shelf=self.shelf)
            Decision.objects.filter(pk=item.pk).update(created_at=datetime(2026, 10, day, 12, tzinfo=timezone.utc))
        result = self.client.get("/keputusan/", {"dari": "2026-10-02", "sampai": "2026-10-02"},
                                 HTTP_ACCEPT="application/json").json()
        self.assertEqual(result["total"], 1)
        self.assertTrue(result["items"][0]["created_at"].startswith("2026-10-02"))
        result = self.client.get("/keputusan/", {"dari": "2026-02-30", "sampai": "bukan-tanggal"},
                                 HTTP_ACCEPT="application/json").json()
        self.assertEqual(result["total"], 3)
        self.assertEqual(len(result["notices"]), 2)
        self.assertIn("diabaikan", result["html"])
        for index in range(10):
            Decision.objects.create(user=self.user, product=self.product, shelf=self.shelf)
        params = {"q": "Produk", "shelf": str(self.shelf.pk), "dari": "2026-10-01"}
        response = self.client.get("/keputusan/", params)
        next_params = parse_qs(urlsplit(response.context["next_url"]).query)
        self.assertEqual(next_params, {"q": ["Produk"], "shelf": [str(self.shelf.pk)], "dari": ["2026-10-01"], "page": ["2"]})
        self.assertEqual(self.client.get("/keputusan/", {"page": "tidak-valid"}, HTTP_ACCEPT="application/json").json()["page"], 1)
        self.assertEqual(self.client.get("/keputusan/", {"page": 999}, HTTP_ACCEPT="application/json").json()["page"], 2)

    def test_filters_never_return_another_users_history_or_inactive_product_search(self):
        other = make_user("lain")
        Decision.objects.create(user=other, product=self.product, shelf=self.shelf, note="Rahasia")
        inactive = make_product(product_name="Produk lama", is_active=False)
        Decision.objects.create(user=self.user, product=inactive)
        self.client.force_login(self.user)
        result = self.client.get("/keputusan/", {"q": "Produk"}, HTTP_ACCEPT="application/json").json()
        self.assertEqual(result["items"], [])
        self.assertNotIn("Rahasia", result["html"])
        result = self.client.get("/keputusan/", {"shelf": self.shelf.pk}, HTTP_ACCEPT="application/json").json()
        self.assertEqual(result["total"], 0)

    def test_ajax_write_requires_csrf_and_returns_refreshed_list_fragment(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/keputusan/tambah/", {"product": self.product.pk}).status_code, 403)
        client.get("/keputusan/")
        headers = {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value, "HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
        response = client.post("/keputusan/tambah/", {"product": self.product.pk, "note": "Ditambahkan lewat AJAX"}, **headers)
        self.assertEqual(response.status_code, 201)
        item = response.json()["item"]
        result = client.get("/keputusan/", **headers).json()
        self.assertIn("Ditambahkan lewat AJAX", result["html"])
        self.assertEqual(client.post(f"/keputusan/{item['id']}/ubah/", {"note": "Diubah"}, **headers).status_code, 200)
        self.assertEqual(client.post(f"/keputusan/{item['id']}/hapus/", **headers).status_code, 200)
        self.assertEqual(client.get("/keputusan/", **headers).json()["total"], 0)

    def test_note_update_ignores_forged_owner_product_and_shelf(self):
        decision = Decision.objects.create(user=self.user, product=self.product, shelf=self.shelf)
        other = make_user("lain")
        other_product = make_product(product_name="Produk lain")
        other_shelf = make_shelf(other, other_product, is_private=True)
        self.client.force_login(self.user)
        response = self.client.post(f"/keputusan/{decision.pk}/ubah/", {
            "note": "Alasan berubah", "user": other.pk, "product": other_product.pk, "shelf": other_shelf.pk,
        }, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        item = response.json()["item"]
        self.assertEqual((item["product_id"], item["shelf_id"], item["note"]),
                         (self.product.pk, self.shelf.pk, "Alasan berubah"))
        self.client.force_login(other)
        self.assertEqual(self.client.get("/keputusan/", HTTP_ACCEPT="application/json").json()["items"], [])
