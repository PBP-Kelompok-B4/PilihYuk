from django.test import TestCase

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
