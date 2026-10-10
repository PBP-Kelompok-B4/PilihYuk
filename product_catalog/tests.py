from datetime import timedelta
import tempfile
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from .models import Product, ProductView
from . import open_food_facts as off
from .off_mapping import product_fields


NUTRIENTS = (
    "energy_kcal_100g", "proteins_100g", "fat_100g", "saturated_fat_100g",
    "carbohydrates_100g", "sugars_100g", "fiber_100g", "sodium_100g",
)
LIST_FIELDS = (
    "allergens", "categories_tags", "packaging_tags", "labels_tags",
    "ingredients_analysis_tags", "misc_tags",
)


class ProductTests(TestCase):
    def test_minimal_manual_product(self):
        product = Product(source="manual")
        product.full_clean()
        product.save()
        product.refresh_from_db()
        self.assertIsNotNone(product.pk)
        self.assertIsNone(product.code)
        self.assertIsNone(product.added_by)
        self.assertEqual(product.product_name, "")

    def test_code_preserves_leading_zeroes(self):
        product = Product.objects.create(source="off", code="0089686010947")
        product.refresh_from_db()
        self.assertEqual(product.code, "0089686010947")

    def test_code_maximum_length(self):
        product = Product(source="manual", code="12345678901234")
        product.full_clean()
        product.code += "5"
        with self.assertRaises(ValidationError) as error:
            product.full_clean()
        self.assertIn("code", error.exception.message_dict)

    def test_duplicate_non_null_code_is_rejected(self):
        Product.objects.create(source="off", code="0089686010947")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.create(source="manual", code="0089686010947")

    def test_multiple_products_without_barcode(self):
        first = Product.objects.create(source="manual", code=None)
        second = Product.objects.create(source="manual", code=None)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(Product.objects.filter(code__isnull=True).count(), 2)

    def test_product_starts_active(self):
        product = Product.objects.create(source="manual")
        product.refresh_from_db()
        self.assertTrue(product.is_active)

    def test_deleting_adding_user_preserves_product(self):
        user = get_user_model().objects.create_user(username="owner")
        product = Product.objects.create(source="manual", added_by=user)
        user.delete()
        product.refresh_from_db()
        self.assertIsNone(product.added_by_id)

    def test_nutrient_zeroes_are_preserved(self):
        product = Product(source="manual", **dict.fromkeys(NUTRIENTS, 0))
        product.full_clean()
        product.save()
        product.refresh_from_db()
        for field in NUTRIENTS:
            with self.subTest(field=field):
                self.assertEqual(getattr(product, field), 0)

    def test_unavailable_nutrients_are_null(self):
        product = Product(source="manual", **dict.fromkeys(NUTRIENTS, None))
        product.full_clean()
        product.save()
        product.refresh_from_db()
        for field in NUTRIENTS:
            with self.subTest(field=field):
                self.assertIsNone(getattr(product, field))

    def test_documented_grades_round_trip(self):
        cases = {
            "nutrition_grade": ("a", "b", "c", "d", "e", "unknown", "not-applicable"),
            "environmental_grade": ("a-plus", "a", "b", "c", "d", "e", "f", "unknown", "not-applicable"),
        }
        for field, grades in cases.items():
            for grade in grades:
                with self.subTest(field=field, grade=grade):
                    product = Product(source="off", **{field: grade})
                    product.full_clean()
                    product.save()
                    product.refresh_from_db()
                    self.assertEqual(getattr(product, field), grade)

    def test_invalid_official_grades_fail_validation(self):
        for field, value in (("nutrition_grade", "f"), ("environmental_grade", "g")):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as error:
                    Product(source="manual", **{field: value}).full_clean()
                self.assertIn(field, error.exception.message_dict)

    def test_missing_grades_and_estimate(self):
        product = Product.objects.create(source="manual")
        product.refresh_from_db()
        self.assertEqual(product.nutrition_grade, "unknown")
        self.assertEqual(product.environmental_grade, "unknown")
        self.assertEqual(product.environmental_grade_estimated, "")

    def test_estimate_has_no_fixed_choices(self):
        product = Product(source="manual", environmental_grade_estimated="future-estimate")
        product.full_clean()
        product.save()
        product.refresh_from_db()
        self.assertEqual(product.environmental_grade_estimated, "future-estimate")

    def test_nova_allows_missing_and_documented_groups(self):
        for value in (None, 1, 2, 3, 4):
            with self.subTest(value=value):
                product = Product(source="manual", nova_group=value)
                product.full_clean()
                product.save()
                product.refresh_from_db()
                self.assertEqual(product.nova_group, value)
        for value in (0, 5):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    Product(source="manual", nova_group=value).full_clean()

    def test_list_defaults_are_independent_and_persist_as_lists(self):
        first = Product(source="manual")
        second = Product(source="manual")
        for field in LIST_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(getattr(first, field), [])
                getattr(first, field).append("en:example")
                self.assertEqual(getattr(second, field), [])
        first.save()
        second.save()
        first.refresh_from_db()
        second.refresh_from_db()
        for field in LIST_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(getattr(first, field), ["en:example"])
                self.assertEqual(getattr(second, field), [])

    def test_never_synced_products_have_null_timestamp(self):
        for source in ("off", "manual"):
            with self.subTest(source=source):
                product = Product.objects.create(source=source)
                product.refresh_from_db()
                self.assertIsNone(product.last_synced_at)

    def test_required_filter_indexes_exist_in_database(self):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, Product._meta.db_table)
        indexed_columns = [item["columns"] for item in constraints.values() if item["index"]]
        self.assertIn(["category"], indexed_columns)
        self.assertIn(["nutrition_grade"], indexed_columns)

    def test_automatic_product_timestamps(self):
        created = timezone.now()
        updated = created + timedelta(seconds=1)
        with patch("django.utils.timezone.now", return_value=created):
            product = Product.objects.create(source="manual")
        with patch("django.utils.timezone.now", return_value=updated):
            product.product_name = "Updated name"
            product.save()
        product.refresh_from_db()
        self.assertEqual(product.created_at, created)
        self.assertEqual(product.updated_at, updated)
        self.assertIsNone(product.last_synced_at)

    def test_only_documented_sources_are_accepted(self):
        with self.assertRaises(ValidationError) as error:
            Product(source="other").full_clean()
        self.assertIn("source", error.exception.message_dict)


class ProductViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="viewer")
        self.product = Product.objects.create(source="manual")

    def test_view_has_relationships_and_creation_timestamp(self):
        viewed = timezone.now()
        with patch("django.utils.timezone.now", return_value=viewed):
            record = ProductView.objects.create(user=self.user, product=self.product)
        record.refresh_from_db()
        self.assertEqual(record.user, self.user)
        self.assertEqual(record.product, self.product)
        self.assertEqual(record.viewed_at, viewed)

    def test_repeated_views_are_separate_rows(self):
        first = ProductView.objects.create(user=self.user, product=self.product)
        second = ProductView(user=self.user, product=self.product)
        second.full_clean()
        second.save()
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(ProductView.objects.filter(user=self.user, product=self.product).count(), 2)

    def test_deleting_user_cascades_to_views(self):
        record = ProductView.objects.create(user=self.user, product=self.product)
        self.user.delete()
        self.assertFalse(ProductView.objects.filter(pk=record.pk).exists())
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_deleting_product_cascades_to_views(self):
        record = ProductView.objects.create(user=self.user, product=self.product)
        self.product.delete()
        self.assertFalse(ProductView.objects.filter(pk=record.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())
class NormalizeBarcodeTests(SimpleTestCase):
    def test_check_digit_and_non_ascii_input(self):
        self.assertTrue(off.has_valid_upc_check_digit("089686010947"))
        for value in (None, "089686010948", "123", "²" * 12):
            self.assertFalse(off.has_valid_upc_check_digit(value))
        self.assertEqual(off.normalize_barcode("²abc"), "")

    def test_matches_open_food_facts_rules(self):
        cases = {
            "089686010947": "0089686010947",  # UPC 12 digit diberi 0 di depan
            "0089686010947": "0089686010947",
            "0000000000017": "00000017",  # menjadi EAN-8
            "17": "00000017",
            "96385074": "96385074",
            "0000096385074": "96385074",
            "034000470693": "0034000470693",
            "123456789": "0000123456789",
            "3017620422003": "3017620422003",
            "03017620422003": "3017620422003",  # 14 digit diawali 0
            "13017620422000": "13017620422000",
            " 3017-6204 22003 ": "3017620422003",  # selain digit dibuang
            "": "",
            "abc": "",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(off.normalize_barcode(raw), expected)
        self.assertIsNone(off.normalize_barcode(None))


class IsSoldInIndonesiaTests(SimpleTestCase):
    def test_only_list_with_indonesia_counts(self):
        self.assertTrue(off.is_sold_in_indonesia({"countries_tags": ["en:france", "en:indonesia"]}))
        self.assertFalse(off.is_sold_in_indonesia({"countries_tags": ["en:france"]}))
        self.assertFalse(off.is_sold_in_indonesia({"countries_tags": []}))
        self.assertFalse(off.is_sold_in_indonesia({"countries_tags": "en:indonesia"}))
        self.assertFalse(off.is_sold_in_indonesia({}))
        self.assertFalse(off.is_sold_in_indonesia(None))


class HasValueTests(SimpleTestCase):
    def test_open_food_facts_empty_markers(self):
        product = {"grade": "b", "unknown": "unknown", "na": "not-applicable", "blank": " ", "tags": []}
        self.assertTrue(off.has_value(product, "grade"))
        for field in ["unknown", "na", "blank", "tags", "missing"]:
            with self.subTest(field=field):
                self.assertFalse(off.has_value(product, field))


class ReadCsvTests(SimpleTestCase):
    def test_keeps_only_indonesian_rows_shaped_like_api(self):
        header = "code\tproduct_name\tcountries_tags\tnutriscore_grade\tnova_group\tsugars_100g\tlabels_tags"
        rows = [
            "089686010947\tMi Goreng\ten:france,en:indonesia\tc\t4.0\t7\ten:halal",
            "3017620422003\tNutella\ten:france\te\t4\t56.3\t",
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "products.csv"
            path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
            products = list(off.read_indonesian_products_from_csv(str(path)))

        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["code"], "089686010947")
        self.assertEqual(product["countries_tags"], ["en:france", "en:indonesia"])
        self.assertEqual(product["labels_tags"], ["en:halal"])
        self.assertEqual(product["nutrition_grades"], "c")
        self.assertEqual(product["nova_group"], 4)
        self.assertEqual(product["nutriments"], {"sugars_100g": 7.0})


class GetJsonTests(SimpleTestCase):
    @mock.patch("product_catalog.open_food_facts.time.sleep")
    @mock.patch("product_catalog.open_food_facts.requests.get")
    def test_all_server_errors_and_429_have_finite_retries(self, fake_get, fake_sleep):
        for status in (429, *range(500, 600)):
            with self.subTest(status=status):
                response = mock.Mock(status_code=status)
                response.raise_for_status.side_effect = off.requests.HTTPError(response=response)
                fake_get.return_value = response
                fake_get.reset_mock()
                fake_sleep.reset_mock()
                with self.assertRaises(off.requests.HTTPError):
                    off.get_json("https://example.test", retry_waits=(2, 5))
                self.assertEqual(fake_get.call_count, 3)
                self.assertEqual(fake_sleep.call_args_list, [mock.call(2), mock.call(5)])
                self.assertEqual(fake_get.call_args.kwargs["timeout"], 10)
                self.assertEqual(fake_get.call_args.kwargs["headers"]["User-Agent"], off.USER_AGENT)
                response.json.assert_not_called()

    @mock.patch("product_catalog.open_food_facts.time.sleep")
    @mock.patch("product_catalog.open_food_facts.requests.get")
    def test_network_retry_recovery_and_exhaustion(self, fake_get, fake_sleep):
        for error in (
            off.requests.Timeout, off.requests.ConnectionError,
            off.requests.exceptions.ChunkedEncodingError,
            off.requests.exceptions.ContentDecodingError,
        ):
            fake_get.side_effect = error("offline")
            fake_get.reset_mock()
            with self.assertRaises(error):
                off.get_json("https://example.test", retry_waits=(2, 5))
            self.assertEqual(fake_get.call_count, 3)
        ok = mock.Mock(status_code=200)
        ok.json.return_value = {"product": {}}
        fake_get.side_effect = [off.requests.Timeout(), ok]
        self.assertEqual(off.get_json("https://example.test", retry_waits=(2,)), {"product": {}})

    @mock.patch("product_catalog.open_food_facts.time.sleep")
    @mock.patch("product_catalog.open_food_facts.requests.get")
    def test_client_errors_and_invalid_json_are_not_retried(self, fake_get, fake_sleep):
        for status in (400, 401, 403, 404, 422):
            response = mock.Mock(status_code=status)
            response.raise_for_status.side_effect = off.requests.HTTPError(response=response)
            fake_get.return_value = response
            fake_get.reset_mock()
            with self.assertRaises(off.requests.HTTPError):
                off.get_json("https://example.test")
            fake_get.assert_called_once()
        response = mock.Mock(status_code=200)
        response.json.side_effect = ValueError("invalid JSON")
        fake_get.return_value = response
        fake_get.reset_mock()
        with self.assertRaises(ValueError):
            off.get_json("https://example.test")
        fake_get.assert_called_once()
        fake_sleep.assert_not_called()

    @mock.patch("product_catalog.open_food_facts.time.sleep")
    @mock.patch("product_catalog.open_food_facts.requests.get")
    def test_retries_on_503_then_returns_json(self, fake_get, fake_sleep):
        busy = mock.Mock(status_code=503)
        ok = mock.Mock(status_code=200)
        ok.json.return_value = {"product": {"code": "17"}}
        fake_get.side_effect = [busy, ok]

        self.assertEqual(off.get_json("https://example.test", retry_waits=(2,)), {"product": {"code": "17"}})
        fake_sleep.assert_called_once_with(2)


class FetchProductTests(SimpleTestCase):
    @mock.patch("product_catalog.open_food_facts.get_json")
    def test_v3_fields_and_absent_product(self, fake_json):
        fake_json.return_value = {"product": {"code": "0089686010947"}}
        self.assertEqual(off.fetch_product("0089686010947"), {"code": "0089686010947"})
        fake_json.assert_called_once_with(
            off.API_BASE_URL + "/api/v3/product/0089686010947",
            {"fields": ",".join(off.PRODUCT_FIELDS)}, retry_waits=(2, 5),
        )
        fake_json.return_value = {"status": 0}
        self.assertIsNone(off.fetch_product("17"))

    @mock.patch("product_catalog.open_food_facts.get_json")
    def test_only_404_becomes_none(self, fake_json):
        for status in (404, 403, 500):
            fake_json.side_effect = off.requests.HTTPError(response=mock.Mock(status_code=status))
            if status == 404:
                self.assertIsNone(off.fetch_product("17"))
            else:
                with self.assertRaises(off.requests.HTTPError):
                    off.fetch_product("17")


class NumericAndCsvEdgeTests(SimpleTestCase):
    def test_zero_is_present_but_nonfinite_numbers_are_unavailable(self):
        self.assertTrue(off.has_value({"value": 0}, "value"))
        for value in (0, "0", 1.5, "4.0"):
            self.assertTrue(off.is_number(value))
        for value in (None, "", "unknown", "not-applicable", "NaN", "inf", True, 10**400):
            self.assertFalse(off.is_number(value))

    def test_gzip_csv_exact_country_zero_allergens_and_limit(self):
        import gzip
        content = (
            "code\tcountries_tags\tsugars_100g\tfat_100g\tnova_group\tallergens\n"
            "1\ten:indonesia-other\t0\t1\t4\ten:milk\n"
            "2\ten:indonesia\t0\tNaN\t4.5\ten:milk,milk,en:soybeans\n"
            "3\ten:indonesia\t1\t2\t4\t\n"
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "products.csv.gz"
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                stream.write(content)
            records = list(off.read_indonesian_products_from_csv(path, limit=1))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["code"], "2")
        self.assertEqual(records[0]["nutriments"], {"sugars_100g": 0.0})
        self.assertEqual(records[0]["allergens_tags"], ["en:milk", "en:soybeans"])
        self.assertNotIn("nova_group", records[0])


class OffMappingTests(SimpleTestCase):
    def record(self, **values):
        return {"code": "0089686010947", "countries_tags": ["en:indonesia"], **values}

    def test_environmental_precedence_missing_fallback_and_markers(self):
        for primary, fallback, expected in (
            ("a-plus", "f", "a-plus"), ("unknown", "b", "b"),
            ("not-applicable", "c", "c"), (None, "d", "d"),
            (" ", "e", "e"), ("not-applicable", None, "not-applicable"),
            (None, None, "unknown"),
        ):
            with self.subTest(primary=primary, fallback=fallback):
                fields = product_fields(self.record(environmental_score_grade=primary, ecoscore_grade=fallback))
                self.assertEqual(fields["environmental_grade"], expected)
                self.assertEqual(fields["environmental_grade_estimated"], "")

    def test_maps_names_tags_origin_and_nutrient_units_without_guessing(self):
        fields = product_fields(self.record(
            product_name_id="Nama", product_name="Name", product_name_en="English",
            origins_tags=["en:france"], manufacturing_places="Elsewhere",
            labels_tags=["en:halal"], nutriments={"energy-kcal_100g": 0, "sodium_100g": 0.2},
        ))
        self.assertEqual(fields["product_name"], "Nama")
        self.assertEqual(fields["origin"], "france")
        self.assertTrue(fields["halal_labeled"])
        self.assertEqual(fields["energy_kcal_100g"], 0)
        self.assertEqual(fields["sodium_100g"], 0.2)
        self.assertIsNone(fields["sugars_100g"])
        self.assertEqual(fields["allergens"], [])
        empty = product_fields(self.record())
        self.assertEqual(empty["origin"], "")
        self.assertFalse(empty["halal_labeled"])

    def test_rejects_non_indonesian_and_unusable_barcodes(self):
        for record in ({"code": "17", "countries_tags": ["en:france"]}, self.record(code=None), self.record(code="1" * 15)):
            with self.assertRaises(ValueError):
                product_fields(record)


class ProductFixtureTests(TestCase):
    def test_fixture_is_reproducible_and_all_twenty_models_validate(self):
        import json
        from .fixture_data import FIXTURE, build_fixture
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture, build_fixture())
        self.assertEqual(len(fixture), 20)
        self.assertEqual(len({row["fields"]["code"] for row in fixture}), 20)
        for row in fixture:
            product = Product(**row["fields"])
            product.full_clean()
            self.assertEqual(product.source, "off")
        self.assertTrue(any(row["fields"]["halal_labeled"] for row in fixture))
        self.assertTrue(any(row["fields"]["nutrition_grade"] in ("unknown", "not-applicable") for row in fixture))

    def test_seed_is_repeatable_and_preserves_existing_rows_and_ids(self):
        from io import StringIO
        from django.core.management import call_command
        from .fixture_data import CODES
        existing = Product.objects.create(code=CODES[0], source="manual", product_name="My edit", is_active=False)
        unrelated = Product.objects.create(source="manual", product_name="Keep me")
        call_command("seed_products", stdout=StringIO())
        snapshot = list(Product.objects.order_by("pk").values())
        call_command("seed_products", stdout=StringIO())
        self.assertEqual(list(Product.objects.order_by("pk").values()), snapshot)
        self.assertEqual(Product.objects.count(), 21)
        existing.refresh_from_db()
        self.assertEqual(existing.product_name, "My edit")
        self.assertEqual(existing.source, "manual")
        self.assertFalse(existing.is_active)
        self.assertTrue(Product.objects.filter(pk=unrelated.pk, product_name="Keep me").exists())


class CatalogViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(
            source="off", code="0089686010947", product_name="Oat drink", brand="Example",
            category="Minuman", origin="france", nutrition_grade="b", halal_labeled=True,
            sugars_100g=0, sodium_100g=0.2, environmental_grade="not-applicable",
            ingredients_text="<script>alert(1)</script>", allergens=["en:gluten"],
            packaging_tags=["en:carton"],
        )
        cls.other = Product.objects.create(source="manual", product_name="Biscuit", brand="Other", nutrition_grade="unknown")
        cls.hidden = Product.objects.create(source="off", product_name="Hidden product", brand="Secret brand", is_active=False)

    def test_public_list_uses_shared_templates_and_hides_inactive_products(self):
        from django.urls import reverse
        with mock.patch("product_catalog.open_food_facts.requests.get") as network:
            response = self.client.get(reverse("product_catalog:product_list"))
        self.assertEqual(response.status_code, 200)
        for template in ("product_catalog/product_list.html", "base.html", "components/footer.html"):
            self.assertTemplateUsed(response, template)
        self.assertContains(response, "Oat drink")
        self.assertContains(response, "Biscuit")
        self.assertNotContains(response, "Hidden product")
        self.assertNotContains(response, "Secret brand")
        for license_name in ("ODbL", "DbCL", "CC BY-SA"):
            self.assertContains(response, license_name)
        network.assert_not_called()

    def test_each_filter_and_combined_filters(self):
        from django.urls import reverse
        filters = {"category": "Minuman", "brand": "Example", "origin": "france", "nutrition_grade": "b", "halal": "1"}
        for query in [{key: value} for key, value in filters.items()] + [filters]:
            with self.subTest(query=query):
                response = self.client.get(reverse("product_catalog:product_list"), query)
                self.assertQuerySetEqual(response.context["products"], [self.product])
        response = self.client.get(reverse("product_catalog:product_list"), {"nutrition_grade": "unknown"})
        self.assertQuerySetEqual(response.context["products"], [self.other])

    def test_search_matches_name_brand_or_barcode(self):
        from django.urls import reverse
        for query in ("oAt", "Example", "0089686010947"):
            response = self.client.get(reverse("product_catalog:product_list"), {"q": query})
            self.assertQuerySetEqual(response.context["products"], [self.product])

    def test_empty_and_no_match_states(self):
        from django.urls import reverse
        response = self.client.get(reverse("product_catalog:product_list"), {"q": "not-present"})
        self.assertContains(response, "Belum ada produk yang cocok.")
        Product.objects.update(is_active=False)
        response = self.client.get(reverse("product_catalog:product_list"))
        self.assertContains(response, "Belum ada produk yang cocok.")

    def test_detail_preserves_zero_unknown_and_escapes_product_content(self):
        from django.urls import reverse
        response = self.client.get(reverse("product_catalog:product_detail", args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "product_catalog/product_detail.html")
        self.assertContains(response, "0 g")
        self.assertContains(response, "200 mg")
        self.assertContains(response, "Belum tersedia")
        self.assertContains(response, "not-applicable")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "https://world.openfoodfacts.org/product/0089686010947")
        self.assertContains(response, "gluten")
        self.assertContains(response, "carton")

    def test_detail_404_for_inactive_or_missing_product(self):
        from django.urls import reverse
        for pk in (self.hidden.pk, 99999):
            self.assertEqual(self.client.get(reverse("product_catalog:product_detail", args=[pk])).status_code, 404)

    def test_manual_detail_has_no_off_link_or_public_creator_identity(self):
        from django.urls import reverse
        user = get_user_model().objects.create_user(username="private-creator-name")
        self.other.added_by = user
        self.other.save()
        response = self.client.get(reverse("product_catalog:product_detail", args=[self.other.pk]))
        self.assertNotContains(response, "Lihat di Open Food Facts")
        self.assertNotContains(response, user.username)

    def test_detail_does_not_record_views_even_when_logged_in(self):
        from django.urls import reverse
        user = get_user_model().objects.create_user(username="reader")
        self.client.force_login(user)
        url = reverse("product_catalog:product_detail", args=[self.product.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(ProductView.objects.count(), 0)

    def test_search_input_is_escaped(self):
        from django.urls import reverse
        response = self.client.get(reverse("product_catalog:product_list"), {"q": '"><script>alert(2)</script>'})
        self.assertContains(response, "&lt;script&gt;alert(2)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(2)</script>")
