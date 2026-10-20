"""Opt-in real dataset integration; writes only Django's isolated test database."""
import hashlib
import json
import os
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Product, ProductView
from .open_food_facts import read_indonesian_products_from_csv, normalize_barcode
from .seed_exclusions import load_seed_exclusions
from .seed_dataset import load_seed_dataset, FINAL_FIXTURE


@skipUnless(os.environ.get("PILIHYUK_FINAL_CSV"), "Set PILIHYUK_FINAL_CSV for the real 406-row integration test")
class FinalDatasetTests(TestCase):
    def test_actual_dataset_import_repeat_fixture_and_user_relations(self):
        source = Path(os.environ["PILIHYUK_FINAL_CSV"])
        records = list(read_indonesian_products_from_csv(source))
        codes = {normalize_barcode(row["code"]) for row in records}
        self.assertEqual(len(records), 406)
        self.assertEqual(len(codes), 406)
        self.assertEqual(codes, set(load_seed_dataset()["canonical_barcodes"]))
        self.assertEqual(codes & load_seed_exclusions(), set(load_seed_dataset()["seed_only_exclusion_overrides"]))
        self.assertEqual(len(codes & load_seed_exclusions()), 62)
        self.assertTrue(all(row["nutriscore_grade"] in "abcde" and len(row["nutriscore_grade"]) == 1 for row in records))

        def seed():
            output = StringIO()
            call_command("seed_products", csv=str(source), stdout=output)
            return json.loads(output.getvalue())

        self.assertFalse(Product.objects.exists())
        first = seed()
        self.assertEqual((first["accepted"], first["created"], first["errors"]), (406, 406, 0))
        self.assertEqual(first["accepted_without_valid_nutriscore"], 0)
        self.assertEqual(Product.objects.filter(is_active=True).count(), 406)
        self.assertEqual(self.client.get(reverse("product_catalog:product_list") + "?format=json").json()["count"], 406)
        user = get_user_model().objects.create_user(username="final-dataset-owner")
        imported = Product.objects.order_by("pk").first()
        imported.product_name = "Preserve local correction"
        imported.save(update_fields=["product_name", "updated_at"])
        collision = Product.objects.order_by("pk")[1]
        collision.source, collision.added_by, collision.is_active = "manual", user, False
        collision.save(update_fields=["source", "added_by", "is_active", "updated_at"])
        manual = Product.objects.create(source="manual", product_name="Unrelated manual", added_by=user)
        history = ProductView.objects.create(user=user, product=imported)
        def snapshot():
            return hashlib.sha256(json.dumps(list(Product.objects.order_by("pk").values()), default=str, sort_keys=True).encode()).hexdigest()
        before = snapshot()
        repeat = seed()
        self.assertEqual((repeat["created"], repeat["updated"], repeat["errors"]), (0, 0, 0))
        self.assertEqual(Product.objects.count(), 407)
        self.assertEqual(snapshot(), before)
        self.assertTrue(ProductView.objects.filter(pk=history.pk, user=user, product=imported).exists())
        self.assertTrue(Product.objects.filter(pk=manual.pk, source="manual", added_by=user).exists())
        with TemporaryDirectory() as folder:
            fixture = Path(folder) / "final-products.json"
            call_command("build_off_fixture", csv=str(source), output=str(fixture), limit=406, stdout=StringIO())
            exported = json.loads(fixture.read_text(encoding="utf-8"))
            self.assertEqual(len(exported), 406)
            self.assertEqual({row["fields"]["code"] for row in exported}, codes)
            self.assertEqual(exported, json.loads(FINAL_FIXTURE.read_text(encoding="utf-8")))
            call_command("seed_products", fixture=str(fixture), stdout=StringIO())
            self.assertEqual(snapshot(), before)
        print("FINAL DATASET: first created=406; repeat created=0 updated=0; fixture=406; manual/history preserved")
