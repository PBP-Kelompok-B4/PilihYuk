from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.tests import make_user
from product_catalog.models import Product

from .models import Shelf, ShelfItem
from .views import PAGE_SIZE


class ShelfListApiTests(APITestCase):
    def setUp(self):
        self.owner = make_user()
        self.public = Shelf.objects.create(name="Mie instan", store_context="Alfamart", owner=self.owner)
        Shelf.objects.create(name="Rahasia", owner=self.owner, is_private=True)
        ShelfItem.objects.create(shelf=self.public, product=Product.objects.create(product_name="A", source="manual"))
        ShelfItem.objects.create(shelf=self.public, product=Product.objects.create(
            product_name="B", source="manual", is_active=False))

    def test_lists_public_shelves_without_email(self):
        r = self.client.get(reverse("shelves_api:list"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["count"], 1)
        shelf = r.json()["results"][0]
        self.assertEqual((shelf["name"], shelf["owner"], shelf["item_count"]), ("Mie instan", "Rani Ayu", 1))
        self.assertNotIn("rani@email.com", r.content.decode())

    def test_search_and_pagination(self):
        Shelf.objects.bulk_create(Shelf(name=f"Kopi {i}", owner=self.owner) for i in range(PAGE_SIZE))
        r = self.client.get(reverse("shelves_api:list"), {"q": "kopi", "page": 2})
        self.assertEqual((r.json()["count"], r.json()["num_pages"], r.json()["page"]), (PAGE_SIZE, 1, 1))
        self.assertEqual(self.client.get(reverse("shelves_api:list"), {"q": "alfa"}).json()["count"], 1)

    def test_post_is_not_allowed(self):
        self.assertEqual(self.client.post(reverse("shelves_api:list")).status_code, 405)
