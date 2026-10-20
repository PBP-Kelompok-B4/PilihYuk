import gzip
import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models.deletion import PROTECT
from django.test import TestCase
from django.urls import reverse

from .models import Product, ProductView


class CatalogCompletionTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="owner@example.org")
        self.other = get_user_model().objects.create_user(username="other@example.org")
        self.staff = get_user_model().objects.create_user(username="curator@example.org", is_staff=True)
        self.product = Product.objects.create(source="manual", product_name="Original", added_by=self.owner)

    def url(self, name, product=None):
        return reverse("product_catalog:" + name, args=[(product or self.product).pk])

    def test_pagination_html_json_and_partial_share_filters(self):
        for index in range(15):
            Product.objects.create(source="manual", product_name=f"Item {index:02}", brand="Test")
        url = reverse("product_catalog:product_list")
        with patch("product_catalog.open_food_facts.requests.get") as http:
            response = self.client.get(url, {"brand": "Test", "format": "json", "page": 2})
            self.assertEqual(response.json()["count"], 15)
            self.assertEqual(response.json()["page"], 2)
            self.assertEqual(len(response.json()["results"]), 3)
            partial = self.client.get(url, {"brand": "Test", "partial": 1, "page": 2})
            self.assertContains(partial, "Halaman 2 / 2")
            self.assertNotContains(partial, "<html")
            self.assertContains(partial, "brand=Test")
            html = self.client.get(url)
            self.assertContains(html, "js/product_catalog.js")
            self.assertContains(html, "catalog-status")
            self.assertEqual(self.client.get(url, {"page": "invalid"}).context["page_obj"].number, 1)
            http.assert_not_called()

    def test_json_privacy_units_missing_values_and_metadata(self):
        self.product.sugars_100g = 0
        self.product.save()
        url = self.url("product_detail")
        public = self.client.get(url, {"format": "json"}).json()
        self.assertNotIn("added_by", public)
        self.assertEqual(public["sugars_100g"], 0)
        self.assertIsNone(public["sodium_100g"])
        self.assertEqual(public["nutrition_grade"], "unknown")
        self.assertIsNone(public["off_url"])
        self.assertFalse(ProductView.objects.exists())
        self.client.force_login(self.other)
        data = self.client.get(url, HTTP_ACCEPT="application/json").json()
        self.assertEqual(data["added_by"], self.owner.pk)
        self.assertEqual(ProductView.objects.get().user, self.other)
        self.assertEqual(self.client.get(reverse("product_catalog:product_list"), {"format": "json"}).json()["results"][0]["added_by"], self.owner.pk)

    def test_anonymous_mutations_and_history_have_json_401(self):
        for url in (self.url("product_edit"), self.url("product_delete"),
                    reverse("product_catalog:product_history"), reverse("product_catalog:product_lookup"),
                    reverse("product_catalog:product_add_manual")):
            self.assertEqual(self.client.post(url + "?format=json").status_code, 401)

    def test_owner_and_curator_edit_manual_without_changing_identity(self):
        for user in (self.owner, self.staff):
            self.client.force_login(user)
            response = self.client.post(self.url("product_edit") + "?format=json", {
                "product_name": "Edited", "source": "off", "code": "123", "added_by": self.other.pk,
                "sugars_100g": "0", "sodium_100g": "0.2", "allergens": '["en:milk"]',
            })
            self.assertEqual(response.status_code, 200)
            self.product.refresh_from_db()
            self.assertEqual(self.product.source, "manual")
            self.assertEqual(self.product.added_by, self.owner)
            self.assertIsNone(self.product.code)
            self.assertEqual(self.product.sugars_100g, 0)
            self.assertEqual(self.product.allergens, ["en:milk"])

    def test_other_user_cannot_edit_or_delete_and_off_is_not_editable(self):
        self.client.force_login(self.other)
        for name in ("product_edit", "product_delete"):
            self.assertEqual(self.client.post(self.url(name), {"product_name": "Attack"}).status_code, 403)
        off = Product.objects.create(source="off", product_name="OFF", added_by=self.owner)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post(self.url("product_edit", off), {"product_name": "Attack"}).status_code, 403)
        self.assertEqual(self.client.post(self.url("product_delete")).status_code, 403)

    def test_invalid_manual_values_do_not_save(self):
        self.client.force_login(self.owner)
        url = reverse("product_catalog:product_add_manual") + "?format=json"
        for fields in ({"allergens": '{"bad":1}'}, {"packaging_tags": '[1]'},
                       {"sugars_100g": "-1"}, {"sodium_100g": "nan"}, {"nutrition_grade": "null"}):
            response = self.client.post(url, {"product_name": "Invalid", **fields})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Product.objects.count(), 1)
        response = self.client.post(url, {"product_name": "Valid", "nova_group": 4, "halal_labeled": "on"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["source"], "manual")

    def test_manual_validation_json_has_error_envelope_and_field_details(self):
        self.client.force_login(self.owner)
        url = reverse("product_catalog:product_add_manual")
        for query, headers in (("?format=json", {}), ("", {"HTTP_ACCEPT": "application/json"})):
            with self.subTest(query=query):
                response = self.client.post(url + query, {"product_name": "", "sugars_100g": "-1"}, **headers)
                self.assertEqual(response.status_code, 400)
                body = response.json()
                self.assertEqual(body["error"]["id"], "validation_error")
                self.assertIsInstance(body["error"]["message"], str)
                self.assertTrue(body["error"]["message"])
                self.assertEqual(body["fields"]["product_name"][0]["code"], "required")
                self.assertTrue(body["fields"]["sugars_100g"][0]["message"])
        self.assertEqual(Product.objects.count(), 1)

    def test_edit_validation_json_has_error_envelope_and_field_details(self):
        self.client.force_login(self.owner)
        url = self.url("product_edit")
        for query, headers in (("?format=json", {}), ("", {"HTTP_ACCEPT": "application/json"})):
            with self.subTest(query=query):
                response = self.client.post(url + query, {"product_name": "", "sugars_100g": "-1"}, **headers)
                self.assertEqual(response.status_code, 400)
                body = response.json()
                self.assertEqual(body["error"]["id"], "validation_error")
                self.assertIsInstance(body["error"]["message"], str)
                self.assertTrue(body["error"]["message"])
                self.assertEqual(body["fields"]["product_name"][0]["code"], "required")
                self.assertTrue(body["fields"]["sugars_100g"][0]["message"])
                self.assertEqual(body["product"]["id"], self.product.pk)
        self.product.refresh_from_db()
        self.assertEqual(self.product.product_name, "Original")

    def test_form_validation_html_and_json_get_are_unchanged(self):
        self.client.force_login(self.owner)
        for url in (reverse("product_catalog:product_add_manual"), self.url("product_edit")):
            with self.subTest(url=url):
                response = self.client.post(url, {"product_name": ""})
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "product_catalog/product_manual.html")
                self.assertEqual(response.context["form"].errors.as_data()["product_name"][0].code, "required")
                response = self.client.get(url + "?format=json")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["fields"], {})
                self.assertNotIn("error", response.json())

    def test_delete_is_post_only_and_preserves_history(self):
        self.client.force_login(self.owner)
        self.client.get(self.url("product_detail"))
        self.assertEqual(self.client.get(self.url("product_delete")).status_code, 405)
        response = self.client.post(self.url("product_delete") + "?format=json")
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)
        self.assertEqual(ProductView.objects.count(), 1)
        self.assertEqual(self.client.get(self.url("product_detail") + "?format=json").status_code, 404)
        self.assertEqual(self.client.get(self.url("product_edit")).status_code, 404)
        self.assertEqual(self.client.get(reverse("product_catalog:product_list") + "?format=json").json()["count"], 0)

    def test_registered_protected_relation_blocks_soft_delete(self):
        # Other modules have no models yet: exercise the declared PROTECT contract.
        relation = Mock(on_delete=PROTECT)
        relation.field.name = "product"
        relation.related_model.objects.filter.return_value.exists.return_value = True
        self.client.force_login(self.owner)
        with patch.object(Product._meta, "related_objects", [relation]):
            response = self.client.post(self.url("product_delete"))
        self.assertEqual(response.status_code, 409)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_active)

    def test_history_is_private_paginated_and_handles_inactive(self):
        for _ in range(13):
            ProductView.objects.create(user=self.owner, product=self.product)
        ProductView.objects.create(user=self.other, product=self.product)
        self.client.force_login(self.owner)
        url = reverse("product_catalog:product_history")
        response = self.client.get(url, {"format": "json", "page": 2})
        self.assertEqual(response.json()["count"], 13)
        self.assertEqual(len(response.json()["results"]), 1)
        self.product.is_active = False
        self.product.save()
        self.assertContains(self.client.get(url), "tidak aktif")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url + "?format=json").json()["count"], 1)

    def test_lookup_json_success_and_error_contract(self):
        self.client.force_login(self.owner)
        url = reverse("product_catalog:product_lookup") + "?format=json"
        self.assertEqual(self.client.get(url).status_code, 200)
        with patch("product_catalog.open_food_facts.requests.get") as http:
            self.assertEqual(self.client.post(url, {"barcode": "bad"}).json()["error"]["id"], "invalid_barcode")
            http.assert_not_called()
            response = Mock(status_code=200)
            response.json.return_value = {"product": {"code": "0089686010947", "product_name": "Mi instan", "countries_tags": ["en:indonesia"], "nutriscore_grade": "a"}}
            http.return_value = response
            self.assertEqual(self.client.post(url, {"barcode": "089686010947"}).json()["code"], "0089686010947")
            response.json.return_value = {"status": 0}
            self.assertEqual(self.client.post(url, {"barcode": "3017620422003"}).json()["error"]["id"], "product_not_found")


class PopulationPipelineTests(TestCase):
    def setUp(self):
        member = patch("product_catalog.seed_dataset.is_seed_member", return_value=True)
        member.start()
        self.addCleanup(member.stop)

    def test_csv_export_is_reproducible_and_does_not_write_database(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / "dump.csv.gz"
            output = Path(folder) / "products.json"
            with gzip.open(source, "wt", encoding="utf-8") as stream:
                stream.write("code\tcountries_tags\tproduct_name\tsugars_100g\tnutriscore_grade\n"
                             "3017620422003\ten:france\tExcluded\t0\ta\n"
                             "0089686010947\ten:indonesia\tMi\t0\ta\n"
                             "0089686010947\ten:indonesia\tDuplicate\t1\ta\n"
                             "1\ten:indonesia\tShort source code\t0\ta\n"
                             "8886008101053\ten:indonesia\tFood\tNaN\ta\n")
            args = {"csv": str(source), "output": str(output), "limit": 10, "stdout": StringIO()}
            call_command("build_off_fixture", **args)
            first = output.read_bytes()
            call_command("build_off_fixture", **args)
            self.assertEqual(output.read_bytes(), first)
            rows = json.loads(first)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["fields"]["sugars_100g"], 0)
            self.assertFalse(Product.objects.exists())
            self.assertEqual(len(json.loads(output.with_suffix(".json.provenance.json").read_text())["source_sha256"]), 64)

    def test_csv_export_invalid_options_and_missing_source(self):
        for args in ({"csv": "missing.csv", "output": "missing.csv", "limit": 10},
                     {"csv": "missing.csv", "output": "unused.json", "limit": 0},
                     {"csv": "missing.csv", "output": "unused.json", "limit": 10}):
            with self.assertRaises(CommandError):
                call_command("build_off_fixture", stdout=StringIO(), **args)

    def test_seed_failure_rolls_back_and_preserves_relation(self):
        from .fixture_data import build_fixture
        fixture = build_fixture()
        owner = get_user_model().objects.create_user(username="seed-owner")
        existing = Product.objects.create(code=fixture[0]["fields"]["code"], source="manual", product_name="Keep")
        view = ProductView.objects.create(user=owner, product=existing)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.json"
            fixture[2]["fields"]["nutrition_grade"] = "invalid"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            with self.assertRaises(ValidationError):
                call_command("seed_products", fixture=str(path), stdout=StringIO())
        self.assertEqual(Product.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.product_name, "Keep")
        self.assertTrue(ProductView.objects.filter(pk=view.pk, product=existing).exists())

    def test_seed_rejects_invalid_structure_and_source(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            for data in ({}, [None], [{"model": "product_catalog.product", "fields": {"source": "manual", "code": None}}]):
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(CommandError):
                    call_command("seed_products", fixture=str(path), stdout=StringIO())
        self.assertFalse(Product.objects.exists())
