from unittest.mock import patch

from django.core.management import CommandError
from django.test import SimpleTestCase, TestCase

from . import test_csv_seed
from .models import Product
from .seed_exclusions import load_seed_exclusions
from .seed_dataset import load_seed_dataset


class ReviewedExclusionsTests(SimpleTestCase):
    def test_reviewed_list_has_889_canonical_unique_codes(self):
        self.assertEqual(len(load_seed_exclusions()), 889)


class SeedExclusionsTests(TestCase):
    setUp = test_csv_seed.CsvSeedTests.setUp
    write = test_csv_seed.CsvSeedTests.write
    row = test_csv_seed.CsvSeedTests.row
    run_seed = test_csv_seed.CsvSeedTests.run_seed

    def test_automatic_exclusion_canonical_alias_and_repeat(self):
        excluded = next(code for code in sorted(load_seed_exclusions() - set(load_seed_dataset()["seed_only_exclusion_overrides"])) if len(code) == 13)
        self.write([self.row(excluded, product_name="Food with grade a"),
                    self.row("0" + excluded, product_name="Food alias", nutriscore_grade="unknown"),
                    self.row(product_name="Susu UHT 1 L", nutriscore_grade="a")])
        dry = self.run_seed(dry_run=True)
        self.assertEqual(dry["skip_reasons"]["reviewed_barcode_exclusion"], 2)
        self.assertEqual(dry["accepted"], 1)
        self.assertEqual(dry["accepted_without_valid_nutriscore"], 0)
        self.assertFalse(Product.objects.exists())
        first = self.run_seed()
        self.assertEqual(first["created"], 1)
        self.assertFalse(Product.objects.filter(code=excluded).exists())
        self.assertEqual(self.run_seed()["created"], 0)
        self.assertEqual(Product.objects.get().nutrition_grade, "a")

    def test_missing_exclusions_fail_closed_before_any_write(self):
        self.write([self.row()])
        with patch("product_catalog.management.commands.seed_products.load_seed_exclusions", side_effect=OSError):
            with self.assertRaises(CommandError):
                self.run_seed()
        self.assertFalse(Product.objects.exists())
