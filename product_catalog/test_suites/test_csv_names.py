import csv
from pathlib import Path

from django.core.management import CommandError
from django.test import SimpleTestCase, TestCase

from ..seed.name_eligibility import screen_name
from . import test_csv_seed


class NameRulesTests(SimpleTestCase):
    def test_explicit_indonesian_and_english_nonfood(self):
        for name in ("Nuvo Sabun Mandi", "Pet Shampoo", "Fabric Softener", "Dishwashing Liquid",
                     "Body Wash", "Pasta Gigi", "Sikat Gigi", "Hand Sanitizer", "Parfum",
                     "Skincare", "Pembersih lantai", "Deterjen cair", "Facial Foam"):
            with self.subTest(name=name):
                self.assertTrue(screen_name(name)[0].startswith("non_food:"))

    def test_unusable_names_and_conservative_gibberish(self):
        for name in ("", "   ", "123456", "12-345", "!!!", "asdfghjkl", "QWERTY", "xxx"):
            self.assertIsNotNone(screen_name(name)[0])
        for name in ("XYZ", "S-26", "H2O", "\u304a\u8336", "Zyxq", "ABC"):
            self.assertIsNone(screen_name(name)[0], name)

    def test_food_false_positive_safeguards(self):
        for name in ("Susu UHT 1 L", "Mie Instan 2 Pack", "Vitamin Water", "Ice Cream",
                     "Fish Skin", "Skinless Wieners", "Cream Crackers", "Rice Paper",
                     "Cookies and cream", "Food conditioners"):
            self.assertIsNone(screen_name(name)[0], name)
        self.assertIsNotNone(screen_name("Vitamin Water")[1])

    def test_case_whitespace_and_word_boundaries(self):
        self.assertEqual(screen_name("  SABUN   mandi  "), screen_name("sabun mandi"))
        self.assertIsNone(screen_name("Shampoola cookies")[0])


class CsvNameImportTests(TestCase):
    setUp = test_csv_seed.CsvSeedTests.setUp
    write = test_csv_seed.CsvSeedTests.write
    row = test_csv_seed.CsvSeedTests.row
    run_seed = test_csv_seed.CsvSeedTests.run_seed
    def test_names_report_missing_invalid_scores_and_idempotence(self):
        names = ["Sabun mandi", "Pet Shampoo", "12345", "asdfghjkl",
                 "Susu UHT 1 L", "Mie Instan 2 Pack", "Vitamin Water", "ABC"]
        grades = ["a"] * len(names)
        self.write([self.row(str(8990000000000+i), product_name=name, nutriscore_grade=grade)
                    for i, (name, grade) in enumerate(zip(names, grades))] +
                   [self.row("8990000000099", product_name="Foreign food", countries_tags="en:indonesia-other")])
        report_path = self.path.parent / "decisions.csv"
        dry = self.run_seed(dry_run=True, report_csv=str(report_path))
        self.assertEqual(dry["accepted"], 4)
        self.assertEqual(dry["accepted_without_valid_nutriscore"], 0)
        self.assertEqual(dry["skip_reasons"]["non_food_name"], 2)
        self.assertEqual(dry["skip_reasons"]["unusable_name"], 2)
        self.assertEqual(dry["manual_review"], 2)
        with report_path.open(encoding="utf-8-sig") as stream:
            decisions = list(csv.DictReader(stream))
        self.assertEqual(len(decisions), len(names) + 1)
        self.assertEqual(decisions[-1]["reason"], "non_indonesia")
        self.assertTrue(all(row["reason"] for row in decisions))
        self.assertEqual(self.run_seed()["created"], 4)
        self.assertEqual(self.run_seed()["created"], 0)

    def test_original_name_preserved_and_strict_mapper_unchanged(self):
        from ..models import Product
        from ..seed.off_mapping import product_fields
        self.write([self.row(product_name="  Susu   UHT 1 L  ", nutriscore_grade="a")])
        self.assertEqual(self.run_seed()["created"], 1)
        product = Product.objects.get()
        self.assertEqual(product.product_name, "  Susu   UHT 1 L  ")
        self.assertEqual(product.nutrition_grade, "a")
        with self.assertRaises(ValueError):
            product_fields({"code": product.code, "countries_tags": ["en:indonesia"], "nutriscore_grade": "null"})

    def test_report_cannot_overwrite_source_or_repository(self):
        self.write([self.row()])
        with self.assertRaises(CommandError):
            self.run_seed(dry_run=True, report_csv=str(self.path))
        with self.assertRaises(CommandError):
            self.run_seed(dry_run=True, report_csv=str(Path(__file__).parent / "report.csv"))
