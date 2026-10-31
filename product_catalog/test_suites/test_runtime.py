from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.db import DatabaseError, close_old_connections, connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from ..forms import BarcodeLookupForm, has_valid_gtin
from ..lookup import reserve_off_lookup, save_imported_product
from ..models import OffLookupQuota, Product


CODE = "0089686010947"
RECORD = {"code": CODE, "countries_tags": ["en:indonesia"], "product_name": "Mi",
          "nutriscore_grade": "a", "environmental_score_grade": "a", "ecoscore_grade": "b",
          "nutriments": {"sugars_100g": 0}}


class RuntimeBarcodeTests(SimpleTestCase):
    def test_each_gtin_format_and_normalization(self):
        for raw, expected in (("96385074", "96385074"), ("089686010947", CODE),
                              (CODE, CODE), ("03017620422003", "3017620422003"),
                              ("13017620422000", "13017620422000")):
            with self.subTest(raw=raw):
                self.assertTrue(has_valid_gtin(raw))
                form = BarcodeLookupForm({"barcode": raw})
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data["barcode"], expected)
                bad = raw[:-1] + str((int(raw[-1]) + 1) % 10)
                self.assertFalse(has_valid_gtin(bad))
                self.assertFalse(BarcodeLookupForm({"barcode": bad}).is_valid())

    def test_invalid_lengths_letters_and_unicode(self):
        for value in ("17", "1" * 15, "abc" + CODE, "²" * 12, "", "1" * 9):
            self.assertFalse(BarcodeLookupForm({"barcode": value}).is_valid())
        form = BarcodeLookupForm({"barcode": " 0896-8601 0947 "})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["barcode"], CODE)


class RuntimeLookupTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="lookup-user")
        self.client.force_login(self.user)
        self.url = reverse("product_catalog:product_lookup")
        self.http_patch = patch("product_catalog.open_food_facts.requests.get")
        self.http = self.http_patch.start()
        self.addCleanup(self.http_patch.stop)
        self.sleep_patch = patch("product_catalog.open_food_facts.time.sleep")
        self.sleep_patch.start()
        self.addCleanup(self.sleep_patch.stop)
        self.response = Mock(status_code=200)
        self.response.json.return_value = {"product": RECORD.copy()}
        self.http.return_value = self.response

    def post(self, code=CODE):
        return self.client.post(self.url, {"barcode": code})

    def test_success_and_repeat_use_local_product(self):
        response = self.post("089686010947")
        product = Product.objects.get(code=CODE)
        self.assertRedirects(response, reverse("product_catalog:product_detail", args=[product.pk]))
        self.assertEqual(product.source, "off")
        self.assertEqual(product.added_by, self.user)
        self.assertIsNotNone(product.last_synced_at)
        self.assertEqual(product.sugars_100g, 0)
        self.assertEqual(product.environmental_grade, "a")
        self.post()
        self.assertEqual(Product.objects.count(), 1)
        self.http.assert_called_once()
        self.assertEqual(len(OffLookupQuota.objects.get(user=self.user).timestamps), 1)
        self.assertEqual(self.http.call_args.kwargs["timeout"], 10)

    def test_local_manual_and_inactive_data_is_preserved_without_quota(self):
        product = Product.objects.create(code=CODE, source="manual", product_name="My edit", is_active=False)
        response = self.post()
        self.assertEqual(response.status_code, 409)
        product.refresh_from_db()
        self.assertEqual(product.product_name, "My edit")
        self.assertEqual(product.source, "manual")
        self.assertFalse(product.is_active)
        self.http.assert_not_called()
        self.assertFalse(OffLookupQuota.objects.exists())

    def test_invalid_barcode_does_not_call_off_or_reserve(self):
        for code in ("abc", "17", CODE[:-1] + "8"):
            self.assertEqual(self.post(code).status_code, 400)
        self.http.assert_not_called()
        self.assertFalse(OffLookupQuota.objects.exists())

    def test_not_found_is_controlled_and_counts(self):
        self.response.status_code = 404
        self.response.raise_for_status.side_effect = requests.HTTPError(response=self.response)
        response = self.post()
        self.assertContains(response, "tidak ditemukan", status_code=404)
        self.assertFalse(Product.objects.exists())
        self.assertEqual(len(OffLookupQuota.objects.get(user=self.user).timestamps), 1)

    def test_non_indonesian_offers_working_manual_form(self):
        self.response.json.return_value = {"product": {**RECORD, "countries_tags": ["en:france"]}}
        response = self.post()
        manual_url = reverse("product_catalog:product_add_manual")
        self.assertContains(response, manual_url, status_code=422)
        self.assertFalse(Product.objects.exists())
        self.assertEqual(self.client.get(manual_url).status_code, 200)
        response = self.client.post(manual_url, {"product_name": "Local product", "source": "off", "code": CODE})
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get()
        self.assertEqual(product.source, "manual")
        self.assertEqual(product.added_by, self.user)
        self.assertIsNone(product.code)

    def test_network_failures_are_controlled_and_retries_count_once(self):
        for error in (requests.Timeout, requests.ConnectionError):
            with self.subTest(error=error):
                self.http.side_effect = error("internal details")
                self.http.reset_mock()
                response = self.post()
                self.assertEqual(response.status_code, 503)
                self.assertNotContains(response, "internal details", status_code=503)
                self.assertEqual(self.http.call_count, 3)
        self.assertEqual(len(OffLookupQuota.objects.get(user=self.user).timestamps), 2)
        self.assertFalse(Product.objects.exists())

    def test_http_failures_are_not_false_not_found(self):
        for status, expected, calls in ((429, 503, 3), (503, 503, 3), (403, 502, 1)):
            with self.subTest(status=status):
                self.response.status_code = status
                self.response.raise_for_status.side_effect = requests.HTTPError(response=self.response)
                self.http.reset_mock()
                self.assertEqual(self.post().status_code, expected)
                self.assertEqual(self.http.call_count, calls)
        self.assertFalse(Product.objects.exists())

    def test_malformed_json_and_structures_do_not_create_products(self):
        for payload in ([], {"product": None}, {}):
            self.response.json.return_value = payload
            self.assertEqual(self.post().status_code, 502)
        self.assertFalse(Product.objects.exists())

    def test_invalid_json_is_controlled(self):
        self.response.json.side_effect = ValueError("invalid JSON internals")
        self.assertEqual(self.post().status_code, 502)
        self.assertFalse(Product.objects.exists())

    def test_mapping_model_validation_and_mismatched_code_fail_cleanly(self):
        for record in ({**RECORD, "environmental_score_grade": "null"},
                       {**RECORD, "product_name": "x" * 256},
                       {**RECORD, "code": "3017620422003"}):
            self.response.json.return_value = {"product": record}
            self.assertEqual(self.post().status_code, 502)
        self.assertFalse(Product.objects.exists())

    def test_fourth_call_is_limited_but_local_product_is_not(self):
        self.response.status_code = 404
        self.response.raise_for_status.side_effect = requests.HTTPError(response=self.response)
        for _ in range(3):
            self.assertEqual(self.post().status_code, 404)
        response = self.post()
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
        self.assertEqual(self.http.call_count, 3)
        Product.objects.create(code=CODE, source="manual")
        self.assertEqual(self.post().status_code, 302)
        self.assertEqual(self.http.call_count, 3)
        self.assertEqual(len(OffLookupQuota.objects.get(user=self.user).timestamps), 3)

    def test_quota_is_bound_to_user_across_sessions(self):
        self.response.json.return_value = {"status": 0}
        for _ in range(3):
            self.post()
        self.client.logout()
        self.client.force_login(self.user)
        self.assertEqual(self.post().status_code, 429)
        other = get_user_model().objects.create_user(username="other")
        self.client.force_login(other)
        self.assertEqual(self.post().status_code, 404)

    @patch("product_catalog.views.reserve_off_lookup", side_effect=DatabaseError("internal database error"))
    def test_reservation_storage_failure_prevents_network(self, reserve):
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, "internal database error", status_code=503)
        self.http.assert_not_called()
        self.assertFalse(Product.objects.exists())

    def test_authentication_and_get_do_not_access_off(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.client.logout()
        for url in (self.url, reverse("product_catalog:product_add_manual")):
            self.assertEqual(self.client.post(url, {"barcode": CODE}).status_code, 302)
        self.http.assert_not_called()

    def test_csrf_is_required_for_import(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url, {"barcode": CODE}).status_code, 403)
        self.http.assert_not_called()


class QuotaConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="parallel")

    def test_sliding_window_expiry_boundary(self):
        now = timezone.now()
        with patch("product_catalog.lookup.timezone.now", return_value=now):
            for _ in range(3):
                self.assertEqual(reserve_off_lookup(self.user), 0)
        with patch("product_catalog.lookup.timezone.now", return_value=now + timedelta(seconds=59)):
            self.assertEqual(reserve_off_lookup(self.user), 1)
        with patch("product_catalog.lookup.timezone.now", return_value=now + timedelta(seconds=60)):
            self.assertEqual(reserve_off_lookup(self.user), 0)
        self.assertEqual(len(OffLookupQuota.objects.get(user=self.user).timestamps), 1)

    def test_only_expired_reservations_are_removed(self):
        now = timezone.now()
        OffLookupQuota.objects.create(user=self.user, timestamps=[
            (now - timedelta(seconds=60)).timestamp(),
            (now - timedelta(seconds=30)).timestamp(), now.timestamp(),
        ])
        with patch("product_catalog.lookup.timezone.now", return_value=now):
            self.assertEqual(reserve_off_lookup(self.user), 0)
            self.assertEqual(reserve_off_lookup(self.user), 30)

    def test_simultaneous_reservations_never_exceed_three(self):
        self.check_parallel_reservations(initialize=True)

    def test_simultaneous_first_reservations_use_one_user_row(self):
        self.check_parallel_reservations(initialize=False)
        self.assertEqual(OffLookupQuota.objects.filter(user=self.user).count(), 1)

    def check_parallel_reservations(self, initialize):
        if initialize:
            OffLookupQuota.objects.create(user=self.user)
        barrier = Barrier(6)

        def reserve():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return reserve_off_lookup(self.user)
                except DatabaseError:
                    return "storage-unavailable"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=6) as pool:
            outcomes = list(pool.map(lambda _: reserve(), range(6)))
        count = outcomes.count(0)
        self.assertLessEqual(count, 3)
        self.assertEqual(len(OffLookupQuota.objects.get(user=self.user).timestamps), count)
        # SQLite may fail closed under contention; remaining slots still work.
        for _ in range(3 - count):
            self.assertEqual(reserve_off_lookup(self.user), 0)
        self.assertGreater(reserve_off_lookup(self.user), 0)

    def test_simultaneous_product_inserts_preserve_unique_barcode(self):
        barrier = Barrier(2)

        def save():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return save_imported_product({"code": CODE, "source": "off", "product_name": "Mi instan", "nutrition_grade": "a"}, self.user).pk
                except DatabaseError:
                    return None
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: save(), range(2)))
        self.assertEqual(Product.objects.filter(code=CODE).count(), 1)
        self.assertTrue(any(pk is not None for pk in results))
        product = save_imported_product({"code": CODE, "source": "off", "nutrition_grade": "a", "product_name": "Replacement"}, self.user)
        self.assertEqual(product.product_name, "Mi instan")

    def test_no_database_transaction_during_http_request(self):
        self.client.force_login(self.user)

        def http(*args, **kwargs):
            self.assertFalse(connection.in_atomic_block)
            response = Mock(status_code=200)
            response.json.return_value = {"product": RECORD}
            return response

        with patch("product_catalog.open_food_facts.requests.get", side_effect=http):
            response = self.client.post(reverse("product_catalog:product_lookup"), {"barcode": CODE})
        self.assertEqual(response.status_code, 302)
