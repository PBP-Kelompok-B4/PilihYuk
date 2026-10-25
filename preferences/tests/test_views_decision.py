from django.test import TestCase

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
