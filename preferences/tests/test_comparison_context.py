from django.core.cache import cache
from django.test import TestCase

from .helpers import make_product, make_shelf, make_user


class ComparisonContextTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = make_user()
        self.product = make_product()
        self.second = make_product(product_name="Pembanding")
        self.shelf = make_shelf(self.user, self.product)
        self.shelf.items.create(product=self.second)
        self.client.force_login(self.user)

    def test_count_records_subset_instead_of_all_shelf_items(self):
        self.shelf.items.create(product=make_product())
        response = self.client.post("/riwayat/tambah/", {"product": self.product.pk, "shelf": self.shelf.pk,
            "compared_product_ids": [self.product.pk, self.second.pk], "compared_product_count": 99}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["item"]["compared_product_count"], 2)
