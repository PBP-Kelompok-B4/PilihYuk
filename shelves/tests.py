from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from product_catalog.models import Product

from .forms import DESCRIPTION_MAX
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


class ShelfViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("rani@example.com", "rani@example.com", "pw-12345678", first_name="Rani")
        self.other = User.objects.create_user("bagas@example.com", "bagas@example.com", "pw-12345678")
        self.public = Shelf.objects.create(name="Mie instan", store_context="Alfamart", owner=self.owner)
        self.private = Shelf.objects.create(name="Rahasia", owner=self.owner, is_private=True)

    def test_public_list_hides_private_shelves(self):
        response = self.client.get(reverse("shelves:list"))
        self.assertContains(response, "Mie instan")
        self.assertNotContains(response, "Rahasia")

    def test_search_filters_by_context(self):
        Shelf.objects.create(name="Kopi pagi", owner=self.other)
        response = self.client.get(reverse("shelves:list"), {"q": "alfamart"})
        self.assertContains(response, "Mie instan")
        self.assertNotContains(response, "Kopi pagi")

    def test_list_json_never_exposes_owner_email(self):
        data = self.client.get(reverse("shelves:list"), {"format": "json"}).json()
        self.assertEqual([s["name"] for s in data["results"]], ["Mie instan"])
        self.assertEqual(data["results"][0]["owner"], "Rani")
        self.assertNotIn("rani@example.com", str(data))

    def test_private_shelf_is_404_for_others_and_visible_to_owner(self):
        url = reverse("shelves:detail", args=[self.private.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_detail_lists_only_active_products(self):
        ShelfItem.objects.create(shelf=self.public, product=Product.objects.create(product_name="Sarimi", source="manual"))
        ShelfItem.objects.create(shelf=self.public, product=Product.objects.create(
            product_name="Produk lama", source="manual", is_active=False))
        response = self.client.get(reverse("shelves:detail", args=[self.public.pk]))
        self.assertContains(response, "Sarimi")
        self.assertNotContains(response, "Produk lama")

    def test_create_requires_login(self):
        response = self.client.get(reverse("shelves:create"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('shelves:create')}",
                             fetch_redirect_response=False)

    def test_create_sets_owner_and_visibility(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("shelves:create"),
                                    {"name": "Susu untuk kopi", "store_context": "Kos", "is_private": "True"})
        shelf = Shelf.objects.get(name="Susu untuk kopi")
        self.assertRedirects(response, reverse("shelves:detail", args=[shelf.pk]))
        self.assertEqual(shelf.owner, self.other)
        self.assertTrue(shelf.is_private)

    def test_create_rejects_blank_name_and_long_description(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("shelves:create"), {"name": "", "description": "x" * (DESCRIPTION_MAX + 1)})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].has_error("name"))
        self.assertTrue(response.context["form"].has_error("description"))
        self.assertEqual(Shelf.objects.count(), 2)

    def test_only_owner_can_edit(self):
        url = reverse("shelves:edit", args=[self.public.pk])
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url, {"name": "Dibajak", "is_private": "False"}).status_code, 404)
        self.client.force_login(self.owner)
        self.client.post(url, {"name": "Mie goreng", "is_private": "False"})
        self.public.refresh_from_db()
        self.assertEqual(self.public.name, "Mie goreng")

    def test_delete_needs_post_and_owner(self):
        url = reverse("shelves:delete", args=[self.public.pk])
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.post(url), reverse("shelves:mine"))
        self.assertFalse(Shelf.objects.filter(pk=self.public.pk).exists())

    def test_mine_shows_own_and_saved_public_shelves_only(self):
        theirs = Shelf.objects.create(name="Camilan kantor", owner=self.other)
        hidden = Shelf.objects.create(name="Disembunyikan", owner=self.other, is_private=True)
        SavedShelf.objects.create(user=self.owner, shelf=theirs)
        SavedShelf.objects.create(user=self.owner, shelf=hidden)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("shelves:mine"))
        self.assertEqual({s.name for s in response.context["own"]}, {"Mie instan", "Rahasia"})
        self.assertEqual([s.name for s in response.context["saved"]], ["Camilan kantor"])
