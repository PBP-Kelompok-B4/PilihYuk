from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from preferences.models import Decision, Preference
from product_catalog.models import Product

from .comparison import comparison_rows
from .forms import DESCRIPTION_MAX, ShelfItemForm
from .models import MAX_SHELF_ITEMS, SavedShelf, Shelf, ShelfItem

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

    def test_public_list_is_ordered_by_last_update(self):
        newer = Shelf.objects.create(name="Kopi pagi", owner=self.other)
        self.public.save()
        response = self.client.get(reverse("shelves:list"))
        self.assertTrue(response.context["page"].paginator.object_list.ordered)
        self.assertEqual([s.name for s in response.context["page"]], ["Mie instan", newer.name])

    def test_list_counts_and_shows_only_active_products(self):
        ShelfItem.objects.create(shelf=self.public, product=Product.objects.create(product_name="Sarimi", source="manual"))
        ShelfItem.objects.create(shelf=self.public, product=Product.objects.create(
            product_name="Produk lama", source="manual", is_active=False))
        data = self.client.get(reverse("shelves:list"), {"format": "json"}).json()
        self.assertEqual(data["results"][0]["item_count"], 1)
        response = self.client.get(reverse("shelves:list"))
        self.assertEqual([i.product.product_name for i in response.context["page"][0].items.all()], ["Sarimi"])

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

    def test_pagination_links_keep_other_query_params(self):
        for i in range(13):
            Shelf.objects.create(name=f"Milik {i}", owner=self.owner)
            SavedShelf.objects.create(user=self.owner, shelf=Shelf.objects.create(name=f"Orang {i}", owner=self.other))
        self.client.force_login(self.owner)
        response = self.client.get(reverse("shelves:mine"), {"saved_page": 2})
        self.assertContains(response, "?saved_page=2&amp;page=2")
        self.assertContains(response, "?saved_page=1")
        response = self.client.get(reverse("shelves:list"), {"q": "orang"})
        self.assertContains(response, "?q=orang&amp;page=2")

    def test_mine_shows_own_and_saved_public_shelves_only(self):
        theirs = Shelf.objects.create(name="Camilan kantor", owner=self.other)
        hidden = Shelf.objects.create(name="Disembunyikan", owner=self.other, is_private=True)
        SavedShelf.objects.create(user=self.owner, shelf=theirs)
        SavedShelf.objects.create(user=self.owner, shelf=hidden)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("shelves:mine"))
        self.assertEqual({s.name for s in response.context["own"]}, {"Mie instan", "Rahasia"})
        self.assertEqual([s.name for s in response.context["saved"]], ["Camilan kantor"])


class ShelfItemViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("rani@example.com", "rani@example.com", "pw-12345678")
        self.other = User.objects.create_user("bagas@example.com", "bagas@example.com", "pw-12345678")
        self.shelf = Shelf.objects.create(name="Mie instan", owner=self.owner)
        self.indomie = Product.objects.create(product_name="Indomie Goreng", brand="Indomie", source="manual")
        self.add_url = reverse("shelves:item_add", args=[self.shelf.pk])
        self.client.force_login(self.owner)

    def add(self, product, **headers):
        return self.client.post(self.add_url, {"product": product.pk}, HTTP_ACCEPT="application/json", **headers)

    def test_candidates_filter_in_database_and_skip_inactive(self):
        Product.objects.create(product_name="Sarimi Goreng", source="manual")
        Product.objects.create(product_name="Indomie Lama", source="manual", is_active=False)
        ShelfItem.objects.create(shelf=self.shelf, product=self.indomie)
        data = self.client.get(reverse("shelves:candidates", args=[self.shelf.pk]), {"q": "indomie"}).json()
        self.assertEqual([(p["name"], p["in_shelf"]) for p in data["results"]], [("Indomie Goreng", True)])

    def test_add_returns_json_and_rejects_duplicate(self):
        response = self.add(self.indomie)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["item_count"], 1)
        response = self.add(self.indomie)
        self.assertEqual(response.status_code, 400)
        self.assertIn("sudah ada", response.json()["error"])

    def test_duplicate_that_slips_past_the_form_returns_400(self):
        ShelfItem.objects.create(shelf=self.shelf, product=self.indomie)
        with patch.object(ShelfItemForm, "clean_product", lambda form: form.cleaned_data["product"]), \
                self.assertLogs("shelves.views", "WARNING"):
            response = self.add(self.indomie)
        self.assertEqual(response.status_code, 400)
        self.assertIn("sudah ada", response.json()["error"])
        self.assertEqual(self.shelf.items.count(), 1)

    def test_add_rejects_inactive_product(self):
        old = Product.objects.create(product_name="Lama", source="manual", is_active=False)
        self.assertEqual(self.add(old).status_code, 400)
        self.assertFalse(self.shelf.items.exists())

    def test_shelf_holds_at_most_twelve_products(self):
        for i in range(MAX_SHELF_ITEMS):
            ShelfItem.objects.create(shelf=self.shelf, product=Product.objects.create(product_name=f"P{i}", source="manual"))
        response = self.add(self.indomie)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.shelf.items.count(), MAX_SHELF_ITEMS)

    def test_remove_returns_json(self):
        ShelfItem.objects.create(shelf=self.shelf, product=self.indomie)
        url = reverse("shelves:item_remove", args=[self.shelf.pk, self.indomie.pk])
        self.assertEqual(self.client.post(url, HTTP_ACCEPT="application/json").json(), {"item_count": 0})

    def test_without_javascript_add_redirects_to_edit(self):
        response = self.client.post(self.add_url, {"product": self.indomie.pk})
        self.assertRedirects(response, reverse("shelves:edit", args=[self.shelf.pk]))
        self.assertTrue(self.shelf.items.filter(product=self.indomie).exists())

    def test_only_owner_manages_products(self):
        ShelfItem.objects.create(shelf=self.shelf, product=self.indomie)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("shelves:candidates", args=[self.shelf.pk])).status_code, 404)
        self.assertEqual(self.add(Product.objects.create(product_name="X", source="manual")).status_code, 404)
        url = reverse("shelves:item_remove", args=[self.shelf.pk, self.indomie.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(self.shelf.items.count(), 1)


class ComparisonTests(TestCase):
    def make(self, name, **fields):
        return Product.objects.create(product_name=name, source="manual", **fields)

    def best(self, rows, label):
        row = next(r for r in rows if r["label"] == label)
        return [cell["best"] for cell in row["cells"]]

    def test_best_value_follows_row_direction(self):
        a = self.make("A", nutrition_grade="c", proteins_100g=9, sugars_100g=7, sodium_100g=0.9)
        b = self.make("B", nutrition_grade="b", proteins_100g=8, sugars_100g=6, sodium_100g=0.78)
        rows = comparison_rows([a, b])
        self.assertEqual(self.best(rows, "Nutri-Score"), [False, True])
        self.assertEqual(self.best(rows, "Protein"), [True, False])
        self.assertEqual(self.best(rows, "Gula"), [False, True])
        self.assertEqual(self.best(rows, "Natrium"), [False, True])
        self.assertEqual(self.best(rows, "Energi"), [False, False])

    def test_needs_two_rankable_values(self):
        a = self.make("A", nutrition_grade="b", environmental_grade="unknown", proteins_100g=9)
        b = self.make("B", nutrition_grade="unknown", environmental_grade="not-applicable")
        rows = comparison_rows([a, b])
        self.assertEqual(self.best(rows, "Nutri-Score"), [False, False])
        self.assertEqual(self.best(rows, "Protein"), [False, False])
        green = next(r for r in rows if r["label"] == "Green-Score")["cells"]
        self.assertEqual([(c["value"], c["rank"]) for c in green], [("unknown", None), ("not-applicable", None)])

    def test_equal_values_are_not_marked(self):
        rows = comparison_rows([self.make("A", nova_group=4), self.make("B", nova_group=4)])
        self.assertEqual(self.best(rows, "NOVA"), [False, False])

    def test_estimate_shows_only_without_official_score_and_is_not_ranked(self):
        a = self.make("A", environmental_grade="unknown", environmental_grade_estimated="a")
        b = self.make("B", environmental_grade="c", environmental_grade_estimated="b")
        c = self.make("C", environmental_grade="d")
        green = next(r for r in comparison_rows([a, b, c]) if r["label"] == "Green-Score")["cells"]
        self.assertEqual([cell["estimate"] for cell in green], ["a", "", ""])
        self.assertEqual([cell["best"] for cell in green], [False, True, False])

    def test_detail_compares_at_most_four_chosen_products(self):
        owner = get_user_model().objects.create_user("rani@example.com", "rani@example.com", "pw-12345678")
        shelf = Shelf.objects.create(name="Mie", owner=owner)
        products = [self.make(f"P{i}") for i in range(6)]
        for product in products:
            ShelfItem.objects.create(shelf=shelf, product=product)
        url = reverse("shelves:detail", args=[shelf.pk])
        self.assertEqual(self.client.get(url, {"format": "json"}).json()["compared"], [p.pk for p in products[:4]])
        chosen = [products[5].pk, products[4].pk] + [p.pk for p in products[:3]]
        data = self.client.get(url, {"format": "json", "banding": chosen}).json()
        self.assertEqual(data["compared"], [p.pk for p in products[:3]] + [products[4].pk])
        response = self.client.get(url, {"partial": "1", "banding": [products[5].pk]})
        self.assertTemplateUsed(response, "shelves/_comparison.html")
        self.assertContains(response, "P5")
        self.assertNotContains(response, ">P0<")


class SaveShelfTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("rani@example.com", "rani@example.com", "pw-12345678")
        self.other = User.objects.create_user("bagas@example.com", "bagas@example.com", "pw-12345678")
        self.shelf = Shelf.objects.create(name="Mie instan", owner=self.owner)
        self.url = reverse("shelves:save", args=[self.shelf.pk])
        self.client.force_login(self.other)

    def save(self, value, shelf_url=None):
        return self.client.post(shelf_url or self.url, {"saved": value}, HTTP_ACCEPT="application/json")

    def test_save_twice_keeps_one_and_unsave_removes_it(self):
        self.assertEqual(self.save("1").json(), {"saved": True, "save_count": 1})
        self.assertEqual(self.save("1").json(), {"saved": True, "save_count": 1})
        self.assertEqual(self.save("0").json(), {"saved": False, "save_count": 0})

    def test_owner_can_save_own_shelf(self):
        self.client.force_login(self.owner)
        self.assertTrue(self.save("1").json()["saved"])

    def test_private_shelf_of_others_is_404(self):
        private = Shelf.objects.create(name="Rahasia", owner=self.owner, is_private=True)
        self.assertEqual(self.save("1", reverse("shelves:save", args=[private.pk])).status_code, 404)
        self.assertFalse(SavedShelf.objects.exists())

    def test_requires_login_and_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {"saved": "1"}).status_code, 302)
        self.assertFalse(SavedShelf.objects.exists())

    def test_detail_shows_count_without_identities(self):
        self.save("1")
        url = reverse("shelves:detail", args=[self.shelf.pk])
        self.assertContains(self.client.get(url), "Tersimpan di Shelf Saya")
        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertContains(response, "Disimpan 1 pengguna")
        self.assertNotContains(response, "bagas")


class ShelfJsonCrudTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("rani@example.com", "rani@example.com", "pw-12345678", first_name="Rani")
        self.other = User.objects.create_user("bagas@example.com", "bagas@example.com", "pw-12345678")
        self.shelf = Shelf.objects.create(name="Mie instan", owner=self.owner)
        self.client.force_login(self.owner)

    def post(self, url, data=None):
        return self.client.post(url, data or {}, HTTP_ACCEPT="application/json")

    def test_create_returns_shelf_or_field_errors(self):
        response = self.post(reverse("shelves:create"), {"name": "Susu untuk kopi", "is_private": "True"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "Susu untuk kopi")
        self.assertTrue(response.json()["is_private"])
        self.assertEqual(response.json()["owner"], "Rani")
        response = self.post(reverse("shelves:create"), {"name": ""})
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json()["errors"])

    def test_edit_returns_updated_shelf_and_stays_owner_only(self):
        url = reverse("shelves:edit", args=[self.shelf.pk])
        data = self.post(url, {"name": "Mie goreng", "is_private": "False"}).json()
        self.assertEqual((data["id"], data["name"], data["item_count"]), (self.shelf.pk, "Mie goreng", 0))
        self.client.force_login(self.other)
        self.assertEqual(self.post(url, {"name": "Dibajak"}).status_code, 404)

    def test_delete_returns_json(self):
        response = self.post(reverse("shelves:delete", args=[self.shelf.pk]))
        self.assertEqual(response.json(), {"id": self.shelf.pk, "deleted": True})
        self.assertFalse(Shelf.objects.exists())

    def test_mine_returns_own_and_saved_shelves(self):
        theirs = Shelf.objects.create(name="Camilan kantor", owner=self.other)
        SavedShelf.objects.create(user=self.owner, shelf=theirs)
        data = self.client.get(reverse("shelves:mine"), {"format": "json"}).json()
        self.assertEqual([s["name"] for s in data["own"]], ["Mie instan"])
        self.assertEqual([s["name"] for s in data["saved"]], ["Camilan kantor"])
        self.assertNotIn("bagas@example.com", str(data))


class PreferenceIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("rani@example.com", "rani@example.com", "pw-12345678")
        self.shelf = Shelf.objects.create(name="Mie", owner=self.user)
        self.a = Product.objects.create(product_name="A", source="manual", energy_kcal_100g=450, sugars_100g=7)
        self.b = Product.objects.create(product_name="B", source="manual", energy_kcal_100g=400, sugars_100g=9)
        for product in (self.a, self.b):
            ShelfItem.objects.create(shelf=self.shelf, product=product)
        self.client.force_login(self.user)

    def labels(self, rows):
        return [r["label"] for r in rows if r["kind"] == "number"]

    def test_preferred_rows_come_first_and_follow_their_direction(self):
        Preference.objects.create(user=self.user, nutrient="sugar", direction="min", weight=1)
        Preference.objects.create(user=self.user, nutrient="energy", direction="min", weight=3)
        rows = comparison_rows([self.a, self.b], self.user.nutrition_preferences.all())
        self.assertEqual(self.labels(rows)[:3], ["Energi", "Gula", "Protein"])
        self.assertEqual(rows[3]["cells"][1]["best"], True)
        self.assertEqual(self.labels(comparison_rows([self.a, self.b]))[0], "Energi")
        self.assertEqual(comparison_rows([self.a, self.b])[3]["direction"], None)

    def test_detail_uses_viewer_preferences(self):
        Preference.objects.create(user=self.user, nutrient="sugar", direction="min", weight=3)
        data = self.client.get(reverse("shelves:detail", args=[self.shelf.pk]), {"format": "json"}).json()
        self.assertEqual(self.labels(data["rows"])[0], "Gula")
        self.client.logout()
        data = self.client.get(reverse("shelves:detail", args=[self.shelf.pk]), {"format": "json"}).json()
        self.assertEqual(self.labels(data["rows"])[0], "Energi")

    def test_choose_button_records_decision_with_compared_products(self):
        response = self.client.get(reverse("shelves:detail", args=[self.shelf.pk]))
        self.assertContains(response, reverse("preferences:decision_create"))
        self.assertContains(response, 'name="compared_product_ids"', count=4)
        response = self.client.post(reverse("preferences:decision_create"),
                                    {"product": self.b.pk, "shelf": self.shelf.pk,
                                     "compared_product_ids": [self.a.pk, self.b.pk]},
                                    HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 201)
        decision = Decision.objects.get()
        self.assertEqual((decision.product, decision.shelf, decision.compared_product_count), (self.b, self.shelf, 2))

    def test_visitors_do_not_see_choose_button(self):
        self.client.logout()
        self.assertNotContains(self.client.get(reverse("shelves:detail", args=[self.shelf.pk])), "Pilih ini")
