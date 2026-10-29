from django.core.cache import cache
from django.test import TestCase
from preferences.models import Decision

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
        response = self.client.post("/keputusan/tambah/", {"product": self.product.pk, "shelf": self.shelf.pk,
            "compared_product_ids": [self.product.pk, self.second.pk], "compared_product_count": 99}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["item"]["compared_product_count"], 2)

    def test_legacy_request_keeps_count_unknown_and_client_count_is_ignored(self):
        response = self.client.post("/keputusan/tambah/", {"product": self.product.pk, "shelf": self.shelf.pk,
            "compared_product_count": 3}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["item"]["compared_product_count"])

    def test_invalid_subsets_never_create_decisions(self):
        inactive = make_product(is_active=False)
        outside = make_product()
        extra = [make_product() for _ in range(3)]
        for product in extra:
            self.shelf.items.create(product=product)
        for ids, shelf in (([], self.shelf.pk), ([self.product.pk] * 2, self.shelf.pk),
                           ([self.product.pk], ""), ([self.second.pk], self.shelf.pk),
                           ([self.product.pk, outside.pk], self.shelf.pk), ([inactive.pk], self.shelf.pk),
                           (["abc"], self.shelf.pk), ([self.product.pk, self.second.pk, *[p.pk for p in extra]], self.shelf.pk)):
            data = {"product": self.product.pk, "shelf": shelf, "compared_product_ids": ids or [""]}
            response = self.client.post("/keputusan/tambah/", data, HTTP_ACCEPT="application/json")
            self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(Decision.objects.filter(user=self.user).count(), 0)

    def test_count_stays_historical_after_edits_and_deleted_relations(self):
        response = self.client.post("/keputusan/tambah/", {"product": self.product.pk, "shelf": self.shelf.pk,
            "compared_product_ids": [self.product.pk, self.second.pk]}, HTTP_ACCEPT="application/json")
        pk = response.json()["item"]["id"]
        self.shelf.items.filter(product=self.second).delete()
        response = self.client.post(f"/keputusan/{pk}/ubah/", {"note": "Alasan baru", "compared_product_count": 4,
            "compared_product_ids": [self.product.pk]}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.json()["item"]["compared_product_count"], 2)
        self.shelf.delete()
        self.product.delete()
        item = Decision.objects.get(pk=pk)
        self.assertEqual(item.compared_product_count, 2)
        self.assertIsNone(item.product_id)
        self.assertIsNone(item.shelf_id)

    def test_four_products_allowed_but_private_foreign_shelf_rejected(self):
        third, fourth = make_product(), make_product()
        self.shelf.items.create(product=third)
        self.shelf.items.create(product=fourth)
        data = {"product": self.product.pk, "shelf": self.shelf.pk,
                "compared_product_ids": [self.product.pk, self.second.pk, third.pk, fourth.pk]}
        response = self.client.post("/keputusan/tambah/", data, HTTP_ACCEPT="application/json")
        self.assertEqual(response.json()["item"]["compared_product_count"], 4)
        self.client.force_login(make_user("lain"))
        self.shelf.is_private = True
        self.shelf.save()
        self.assertEqual(self.client.post("/keputusan/tambah/", data, HTTP_ACCEPT="application/json").status_code, 400)
