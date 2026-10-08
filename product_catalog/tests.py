from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from .models import Product, ProductView


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
