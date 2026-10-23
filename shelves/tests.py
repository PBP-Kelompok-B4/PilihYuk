from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from product_catalog.models import Product

from .models import SavedShelf, Shelf, ShelfItem


class ShelfModelTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("rani", "rani@example.com", "pw-12345678")
        self.product = Product.objects.create(product_name="Indomie Goreng", source="manual")
        self.shelf = Shelf.objects.create(name="Mie instan", owner=self.owner)

    def test_same_product_only_once_per_shelf(self):
        ShelfItem.objects.create(shelf=self.shelf, product=self.product)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ShelfItem.objects.create(shelf=self.shelf, product=self.product)

    def test_product_in_shelf_cannot_be_deleted(self):
        ShelfItem.objects.create(shelf=self.shelf, product=self.product)
        with self.assertRaises(ProtectedError):
            self.product.delete()

    def test_deleting_shelf_removes_items_and_saves(self):
        ShelfItem.objects.create(shelf=self.shelf, product=self.product)
        SavedShelf.objects.create(user=self.owner, shelf=self.shelf)
        self.shelf.delete()
        self.assertFalse(ShelfItem.objects.exists())
        self.assertFalse(SavedShelf.objects.exists())

    def test_user_saves_a_shelf_only_once(self):
        SavedShelf.objects.create(user=self.owner, shelf=self.shelf)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SavedShelf.objects.create(user=self.owner, shelf=self.shelf)
