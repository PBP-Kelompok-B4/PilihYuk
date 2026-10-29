from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.template import Context, Template
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from pilihyuk.middleware import user_timezone
from pilihyuk.views import comparison_rows, featured_shelf
from product_catalog.models import Product, ProductView
from shelves.models import SavedShelf, Shelf, ShelfItem


# Data sintetis hanya untuk menguji perhitungan tabel, bukan isi landing page.
SAMPLE_PRODUCTS = [
    {"kcal": 447, "protein": 9, "sugar": 7, "sodium": 900},
    {"kcal": 450, "protein": 8, "sugar": 8, "sodium": 850},
    {"kcal": 452, "protein": 7.5, "sugar": 6.5, "sodium": 870},
    {"kcal": 440, "protein": 8.5, "sugar": 6, "sodium": 780},
]


class HomePageTests(TestCase):
    def test_best_values_are_marked(self):
        best = {r["label"]: [c["best"] for c in r["cells"]] for r in comparison_rows(SAMPLE_PRODUCTS)}
        self.assertEqual(best["Kalori"], [False] * 4)  # tidak dinilai
        self.assertEqual(best["Protein"], [True, False, False, False])  # tertinggi
        self.assertEqual(best["Gula"], [False, False, False, True])  # terendah
        self.assertEqual(best["Natrium"], [False, False, False, True])

    def test_missing_values_are_skipped(self):
        products = [{**SAMPLE_PRODUCTS[0], "protein": None}, SAMPLE_PRODUCTS[1], SAMPLE_PRODUCTS[2]]
        protein = next(r for r in comparison_rows(products) if r["label"] == "Protein")
        self.assertEqual([c["best"] for c in protein["cells"]], [False, True, False])
        self.assertEqual(protein["cells"][0]["pct"], 0)

    def test_home_page_renders(self):
        Product.objects.create(source="manual", product_name="Contoh A", proteins_100g=9)
        Product.objects.create(source="manual", product_name="Contoh B", proteins_100g=8)
        response = self.client.get("/")
        self.assertContains(response, "Bandingkan sebelum pilih.")
        self.assertContains(response, "Tertinggi")

    def test_empty_catalog_renders_without_sample_products_or_table(self):
        response = self.client.get("/")
        self.assertContains(response, "Belum ada produk aktif di katalog.")
        self.assertEqual(response.context["shelf"]["products"], [])
        self.assertEqual(response.context["shelf"]["count"], 0)
        self.assertNotContains(response, "<table")
        self.assertNotContains(response, "Indomie Mi Goreng")

    def test_selection_is_active_only_stable_limited_and_one_query(self):
        Product.objects.create(source="off", product_name="000 hidden", is_active=False)
        records = [
            Product.objects.create(source="manual", product_name=name)
            for name in ("Z last", "B second", "A first", "A first", "C third")
        ]
        with self.assertNumQueries(2):
            result = featured_shelf()
        expected = [records[2], records[3], records[1], records[4]]
        self.assertEqual(result["count"], 4)
        self.assertEqual(
            [p["url"] for p in result["products"]],
            [reverse("product_catalog:product_detail", args=[p.pk]) for p in expected],
        )

    def test_most_saved_public_shelf_leads_and_featured_list_uses_real_shelves(self):
        User = get_user_model()
        owner = User.objects.create_user("rani@example.com", "rani@example.com", "pw-12345678", first_name="Rani")
        fan = User.objects.create_user("bagas@example.com", "bagas@example.com", "pw-12345678")
        products = [Product.objects.create(source="manual", product_name=f"P{i}") for i in range(3)]
        quiet = Shelf.objects.create(name="Kopi pagi", owner=owner)
        loved = Shelf.objects.create(name="Mie instan", owner=owner, store_context="Alfamart")
        secret = Shelf.objects.create(name="Rahasia", owner=owner, is_private=True)
        for shelf in (quiet, loved, secret):
            for product in products[:2]:
                ShelfItem.objects.create(shelf=shelf, product=product)
        SavedShelf.objects.create(user=fan, shelf=loved)
        lonely = Shelf.objects.create(name="Satu produk", owner=owner)
        ShelfItem.objects.create(shelf=lonely, product=products[2])
        SavedShelf.objects.create(user=fan, shelf=lonely)
        response = self.client.get("/")
        self.assertEqual(response.context["shelf"]["title"], "Mie instan")
        self.assertContains(response, reverse("shelves:detail", args=[loved.pk]))
        self.assertContains(response, "Shelf publik")
        self.assertEqual([s["title"] for s in response.context["shelves"]], ["Mie instan", "Kopi pagi"])
        self.assertEqual(response.context["shelves"][0]["user"], "Rani")
        self.assertNotContains(response, "Rahasia")
        self.assertNotContains(response, "Satu produk")
        self.assertNotContains(response, "rani@example.com")

    def test_no_public_shelf_shows_empty_state_and_catalog_example(self):
        Product.objects.create(source="manual", product_name="Contoh A")
        response = self.client.get("/")
        self.assertContains(response, "Belum ada shelf publik saat ini.")
        self.assertContains(response, "Contoh dari katalog")

    def test_mapping_uses_stored_values_and_converts_sodium_without_writes(self):
        product = Product.objects.create(
            source="off", product_name="Stored product", brand="Brand", quantity="85 g",
            nutrition_grade=" B ", environmental_grade=" A-PLUS ", nova_group=4,
            energy_kcal_100g=0, proteins_100g=8.5, sugars_100g=0, sodium_100g=0.25,
            image_url="https://example.com/product.jpg",
        )
        before = Product.objects.values().get(pk=product.pk)
        response = self.client.get("/")
        mapped = response.context["shelf"]["products"][0]
        self.assertEqual(mapped, {
            "name": "Stored product", "brand": "Brand · 85 g", "nutri": "b",
            "green": "a-plus", "estimated": False, "nova": 4,
            "kcal": 0, "protein": 8.5, "sugar": 0, "sodium": 250,
            "image": product.image_url,
            "url": reverse("product_catalog:product_detail", args=[product.pk]),
        })
        self.assertContains(response, mapped["url"])
        self.assertContains(response, "Stored product")
        self.assertEqual(Product.objects.values().get(pk=product.pk), before)
        self.assertFalse(ProductView.objects.exists())

    def test_missing_grades_and_nutrients_are_not_fabricated(self):
        product = Product.objects.create(source="manual", product_name="Missing data")
        for grade in ("unknown", "not-applicable", "", "null"):
            with self.subTest(grade=grade):
                Product.objects.filter(pk=product.pk).update(
                    nutrition_grade=grade, environmental_grade=grade,
                )
                mapped = featured_shelf()["products"][0]
                for key in ("nutri", "green", "nova", "kcal", "protein", "sugar", "sodium"):
                    self.assertIsNone(mapped[key], key)
                self.assertFalse(mapped["estimated"])
        self.assertContains(self.client.get("/"), "Tidak diketahui")

    def test_existing_estimate_is_labelled_and_official_grade_takes_precedence(self):
        product = Product.objects.create(
            source="manual", product_name="Estimate", environmental_grade_estimated="C",
        )
        mapped = featured_shelf()["products"][0]
        self.assertEqual((mapped["green"], mapped["estimated"]), ("C", True))
        self.assertContains(self.client.get("/"), "Estimasi")
        Product.objects.filter(pk=product.pk).update(environmental_grade="b")
        mapped = featured_shelf()["products"][0]
        self.assertEqual((mapped["green"], mapped["estimated"]), ("b", False))

    def test_fewer_than_four_products_and_zero_values(self):
        for index in range(3):
            Product.objects.create(
                source="manual", product_name=f"Zero {index}",
                proteins_100g=0, sugars_100g=0, sodium_100g=0,
            )
        response = self.client.get("/")
        self.assertEqual(response.context["shelf"]["count"], 3)
        self.assertEqual(len(response.context["shelf"]["products"]), 3)
        self.assertTrue(all(p["sodium"] == 0 for p in response.context["shelf"]["products"]))
        protein = next(row for row in response.context["rows"] if row["label"] == "Protein")
        self.assertTrue(all(cell == {"value": 0, "pct": 0, "best": True} for cell in protein["cells"]))

    def test_single_known_value_has_no_best_badge(self):
        for products in ([SAMPLE_PRODUCTS[0]], [
            SAMPLE_PRODUCTS[0], {key: None for key in SAMPLE_PRODUCTS[0]},
        ]):
            with self.subTest(products=products):
                self.assertFalse(any(
                    cell["best"] for row in comparison_rows(products) for cell in row["cells"]
                ))
        Product.objects.create(source="manual", product_name="Only one", proteins_100g=9)
        response = self.client.get("/")
        self.assertEqual(response.context["shelf"]["count"], 1)
        self.assertNotContains(response, "Tertinggi")
        self.assertNotContains(response, "Terendah")


class NotFoundPageTests(TestCase):
    def test_unknown_url_uses_custom_404_page(self):
        response = self.client.get("/tentang/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Halaman tidak ditemukan", status_code=404)


class UserTimezoneTests(TestCase):
    def zone_for(self, cookie):
        request = RequestFactory().get("/")
        if cookie is not None:
            request.COOKIES["tz"] = cookie
        return user_timezone(lambda r: HttpResponse(timezone.get_current_timezone_name()))(request).content.decode()

    def test_browser_zone_is_used_and_bad_values_fall_back_to_utc(self):
        self.assertEqual(self.zone_for("Asia/Jakarta"), "Asia/Jakarta")
        for cookie in (None, "", "Bad/Zone", "../../etc/passwd"):
            self.assertEqual(self.zone_for(cookie), "UTC", cookie)

    def test_stored_times_stay_utc_and_display_follows_cookie(self):
        moment = datetime(2026, 10, 28, 17, 30, tzinfo=dt_timezone.utc)
        rendered = user_timezone(lambda r: HttpResponse(Template("{{ t|date:'H:i' }}").render(Context({"t": moment}))))
        request = RequestFactory().get("/")
        request.COOKIES["tz"] = "Asia/Jakarta"
        self.assertEqual(rendered(request).content.decode(), "00:30")
        self.assertEqual(moment.utcoffset().total_seconds(), 0)
