"""CSV regressions use temporary files and Django's isolated test database."""
import csv
import gzip
import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.db import DatabaseError
from django.test import TestCase, SimpleTestCase

from .models import Product, ProductView
from .open_food_facts import read_indonesian_products_from_csv


class CsvSeedTests(TestCase):
    def setUp(self):
        # Parser/mapping unit tests isolate membership; real 406 integration is unmocked.
        member = patch("product_catalog.seed_dataset.is_seed_member", return_value=True)
        member.start()
        self.addCleanup(member.stop)
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "off.csv"

    def write(self, rows, delimiter="\t", encoding="utf-8", compressed=False):
        columns = list(dict.fromkeys(key for row in rows for key in row))
        if compressed:
            self.path = self.path.with_suffix(".csv.gz")
        opener = gzip.open if compressed else open
        with opener(self.path, "wt", encoding=encoding, newline="") as file:
            writer = csv.DictWriter(file, fieldnames=columns, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(rows)

    def row(self, code="0089686010947", **fields):
        return {"code": code, "countries_tags": "en:indonesia", "product_name": "Produk", "nutriscore_grade": "a", **fields}

    def run_seed(self, **options):
        output = StringIO()
        call_command("seed_products", csv=str(self.path), stdout=output, **options)
        return json.loads(output.getvalue())

    def test_exact_sale_country_filter_not_origin_or_substring(self):
        self.write([
            self.row(), self.row("8996001440124", countries_tags="en:france, en:indonesia"),
            self.row("8996001440049", countries_tags="en:france", manufacturing_places="Indonesia"),
            self.row("8996001301142", countries_tags=""),
            self.row("8886467100055", countries_tags="en:indonesia-other"),
        ])
        report = self.run_seed()
        self.assertEqual(Product.objects.count(), 2)
        self.assertEqual(report["rows_read"], 5)
        self.assertEqual(report["indonesia_rows"], 2)
        self.assertEqual(report["skip_reasons"]["non_indonesia"], 3)

    def test_unknown_grades_zero_missing_columns_and_precedence(self):
        self.write([
            self.row(environmental_score_grade="None", ecoscore_grade="b", sugars_100g="0", sodium_100g="0", fat_100g="NaN"),
            self.row("8996001440124", nutriscore_grade="unknown", environmental_score_grade="a-plus", ecoscore_grade="e"),
            self.row("8996001440049", nutriscore_grade="not-applicable", environmental_score_grade="not-applicable"),
            self.row("8996001301142"),
        ])
        report = self.run_seed()
        self.assertEqual(report["created"], 2)
        self.assertEqual(report["accepted_without_valid_nutriscore"], 0)
        self.assertEqual(report["skip_reasons"]["invalid_nutriscore"], 2)
        first = Product.objects.get(code="0089686010947")
        self.assertEqual((first.sugars_100g, first.sodium_100g), (0, 0))
        self.assertIsNone(first.fat_100g)
        self.assertEqual((first.nutrition_grade, first.environmental_grade), ("a", "b"))
        self.assertFalse(Product.objects.filter(code="8996001440124").exists())
        self.assertFalse(Product.objects.filter(code="8996001440049").exists())
        self.assertEqual(Product.objects.get(code="8996001301142").nutrition_grade, "a")
        self.assertEqual(first.misc_tags, [])

    def test_bom_delimiters_gzip_names_and_tags(self):
        for delimiter in ("\t", ",", ";"):
            with self.subTest(delimiter=delimiter):
                self.path = Path(self.folder.name) / "off.csv"
                self.write([self.row(product_name="", product_name_en="Minuman cafÃ©", labels_tags="en:halal,en:organic", allergens="en:milk,milk", origins_tags="en:france")], delimiter, "utf-8-sig", compressed=True)
                report = self.run_seed(dry_run=True)
                self.assertEqual(report["would_create"], 1)
                self.assertEqual(report["delimiter"], delimiter)
        self.run_seed()
        product = Product.objects.get()
        self.assertEqual(product.product_name, "Minuman cafÃ©")
        self.assertEqual(product.origin, "france")
        self.assertEqual(product.allergens, ["en:milk"])
        self.assertTrue(product.halal_labeled)

    def test_idempotent_preserves_manual_corrected_off_and_history(self):
        user = get_user_model().objects.create_user(username="csv-owner")
        manual = Product.objects.create(code="0089686010947", source="manual", product_name="Manual", added_by=user, is_active=False)
        corrected = Product.objects.create(code="8996001440124", source="off", product_name="Corrected", sugars_100g=1)
        view = ProductView.objects.create(user=user, product=corrected)
        before = list(Product.objects.order_by("pk").values())
        self.write([self.row(), self.row(corrected.code), self.row("8996001440049"), self.row("8996001440049")])
        report = self.run_seed(batch_size=1)
        self.assertEqual(report["created"], 1)
        self.assertEqual(report["updated"], 0)
        self.assertEqual(report["skip_reasons"]["existing_barcode"], 2)
        self.assertEqual(report["skip_reasons"]["duplicate_csv"], 1)
        self.assertEqual(list(Product.objects.filter(pk__in=[manual.pk, corrected.pk]).order_by("pk").values()), before)
        snapshot = list(Product.objects.order_by("pk").values())
        self.assertEqual(self.run_seed()["created"], 0)
        self.assertEqual(list(Product.objects.order_by("pk").values()), snapshot)
        self.assertTrue(ProductView.objects.filter(pk=view.pk, product=corrected).exists())

    def test_dry_run_has_no_writes_and_matches_import(self):
        self.write([self.row(), self.row("8996001440124")])
        with patch.object(Product, "save", side_effect=AssertionError("dry-run writes")):
            report = self.run_seed(dry_run=True, batch_size=1)
        self.assertEqual((report["created"], report["would_create"]), (0, 2))
        self.assertFalse(Product.objects.exists())
        self.assertEqual(self.run_seed()["created"], 2)

    def test_bad_rows_counted_and_later_valid_row_imported(self):
        self.write([
            self.row(code="abc"), self.row(code="1" * 15), self.row(code=""),
            self.row("8996001440124", product_name=""),
            self.row("8996001440049", nutriscore_grade="g"),
            self.row("8996001301142", brands="x" * 256), self.row(),
        ])
        report = self.run_seed()
        self.assertEqual(report["created"], 1)
        self.assertEqual(report["skip_reasons"]["invalid_barcode"], 3)
        self.assertEqual(report["skip_reasons"]["unusable_name"], 1)
        self.assertEqual(report["accepted_without_valid_nutriscore"], 0)
        self.assertEqual(report["skip_reasons"]["invalid_nutriscore"], 1)
        self.assertEqual(report["skip_reasons"]["validation"], 1)
        self.assertEqual(report["errors"], 1)
        self.assertEqual(report["skipped"], 6)

    def test_malformed_row_width_is_counted(self):
        self.path.write_text("code\tcountries_tags\tproduct_name\tnutriscore_grade\n1\ten:indonesia\textra\ta\textra\n0089686010947\ten:indonesia\tValid\ta\n", encoding="utf-8")
        report = self.run_seed()
        self.assertEqual((report["created"], report["errors"]), (1, 1))
        self.assertEqual(report["skip_reasons"]["malformed_row"], 1)

    def test_invalid_header_encoding_and_options_fail_without_writes(self):
        for content in (b"code\tproduct_name\n1\tName\n", b"code\tcountries_tags\tcountries_tags\n1\ten:indonesia\ten:indonesia\n", b"code\tcountries_tags\tproduct_name\n1\ten:indonesia\t\xff\n"):
            self.path.write_bytes(content)
            with self.assertRaises(CommandError):
                self.run_seed()
            self.assertFalse(Product.objects.exists())
        for options in ({"batch_size": 0}, {"fixture": "other.json"}):
            with self.assertRaises(CommandError):
                self.run_seed(**options)

    def test_failed_batch_rolls_back_but_previous_batch_is_reported(self):
        self.write([self.row(), self.row("8996001440124"), self.row("8996001440049"), self.row("8996001301142")])
        original = Product.objects.get_or_create
        calls = 0
        def fail_fourth(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise DatabaseError("storage failure")
            return original(*args, **kwargs)
        output = StringIO()
        with patch.object(Product.objects, "get_or_create", side_effect=fail_fourth):
            with self.assertRaises(CommandError):
                call_command("seed_products", csv=str(self.path), batch_size=2, stdout=output)
        report = json.loads(output.getvalue())
        self.assertFalse(report["completed"])
        self.assertEqual(report["created"], 2)
        self.assertEqual(Product.objects.count(), 2)

    def test_all_rows_over_fixture_and_export_limits_are_processed(self):
        self.write([self.row(str(8990000000000 + index)) for index in range(251)])
        report = self.run_seed(batch_size=17)
        self.assertEqual((report["rows_read"], report["created"]), (251, 251))

    def test_canonical_barcode_matches_existing_and_keeps_leading_zero(self):
        self.write([self.row("089686010947"), self.row("0089686010947")])
        report = self.run_seed()
        self.assertEqual(report["created"], 1)
        self.assertEqual(Product.objects.get().code, "0089686010947")
        self.assertEqual(report["skip_reasons"]["duplicate_csv"], 1)

    def test_null_like_name_uses_fallback_and_invalid_first_duplicate_does_not_hide_valid(self):
        self.write([self.row(product_name="null", product_name_en="Fallback", nutriscore_grade="g"),
                    self.row(product_name="None", product_name_en="Fallback"),
                    self.row("8996001440124", product_name="NaN")])
        report = self.run_seed()
        self.assertEqual(report["created"], 1)
        self.assertEqual(Product.objects.get().product_name, "Fallback")
        self.assertEqual(report["skip_reasons"]["unusable_name"], 1)
        self.assertEqual(report["accepted_without_valid_nutriscore"], 0)
        self.assertEqual(report["skip_reasons"]["invalid_nutriscore"], 1)

    def test_unclosed_quoted_record_is_fatal_not_silent_completion(self):
        self.path.write_text('code,countries_tags,product_name\n0089686010947,en:indonesia,"unclosed\n', encoding="utf-8")
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command("seed_products", csv=str(self.path), stdout=output)
        self.assertFalse(json.loads(output.getvalue())["completed"])
        self.assertFalse(Product.objects.exists())

    def test_off_tsv_quotes_are_literal_and_do_not_swallow_following_rows(self):
        self.path.write_text('code\tcountries_tags\tproduct_name\tnutriscore_grade\n0089686010947\ten:indonesia\t"Literal quote\ta\n8996001440124\ten:indonesia\tNext product\ta\n', encoding="utf-8")
        report = self.run_seed()
        self.assertEqual((report["created"], report["rows_read"]), (2, 2))
        self.assertEqual(Product.objects.get(code="0089686010947").product_name, '"Literal quote')


class CsvStreamingTests(SimpleTestCase):
    def test_reader_does_not_read_ahead_or_materialize_dump(self):
        # Iterator refuses to supply a second row until consumer resumes.
        class GuardedFile(StringIO):
            def read(self, *args):
                raise AssertionError("unbounded read")
            def __next__(self):
                if self.tell() >= boundary and not resumed[0]:
                    raise AssertionError("reader consumed later rows eagerly")
                return super().__next__()
        header = "code\tcountries_tags\tproduct_name\n"
        row = "0089686010947\ten:indonesia\tName\n"
        boundary, resumed = len(header + row), [False]
        with patch("product_catalog.open_food_facts.open", return_value=GuardedFile(header + row * 10000)):
            records = read_indonesian_products_from_csv("off.csv")
            self.assertEqual(next(records)["code"], "0089686010947")
            resumed[0] = True
            self.assertEqual(sum(1 for _ in records), 9999)
