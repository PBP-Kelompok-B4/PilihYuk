"""Tes bonus PATCH mine/<pk>/ (ubah usulan selama pending): services.update_correction dan API.

Notes:
- Body PATCH adalah daftar LENGKAP usulan yang baru (KEPUTUSAN F.g): field boleh ditambah atau dihapus,
  minimal satu; produk tidak bisa diganti; item lama dibuat ulang dengan id baru.
- Klien dari api_fixtures (CSRF diperiksa, force_login); helper data diimpor sebagai fungsi dari tests.py.
- Produk uji: lengkap kecuali serat (kosong), merek "Sarimi", natrium 0.3976 g (tampil 397,6 mg).
"""
import re

from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase

from product_catalog.models import Product

from .api_fixtures import api_client, csrf_token
from .constants import APPROVED, PENDING, REJECTED
from .models import DataCorrection, DataCorrectionItem
from .permissions import AUTH_REQUIRED
from .services import approve_item, submit_correction, update_correction
from .tests import (
    DUPLICATE_MESSAGE,
    EMPTY_MESSAGE,
    FORBIDDEN_MESSAGE,
    NOVA_MESSAGE,
    error_of,
    make_complete_product,
    make_correction,
    make_staff,
    make_user,
)
from .tests_api_mine import NOT_FOUND, detail_url
from .tests_api_moderation import ITEM_NOT_FOUND, item_url
from .tests_api_submit import CORRECTION_KEYS, INVALID
from .validators import MESSAGES

NOT_EDITABLE = {
    "detail": "Pengajuan ini sudah mulai ditinjau sehingga tidak bisa diubah.",
    "code": "not_editable",
}
PRODUCT_INACTIVE = {
    "detail": "Produk ini tidak aktif sehingga tidak bisa dikoreksi.",
    "code": "product_inactive",
}


def stored(correction):
    """Isi item di database, mis. {"fiber_100g": (None, "3")} untuk (old_value, proposed_value)."""
    items = DataCorrectionItem.objects.filter(correction_id=correction.pk)
    return {item.field_name: (item.old_value, item.proposed_value) for item in items}


def item_ids(correction):
    return set(DataCorrectionItem.objects.filter(correction_id=correction.pk).values_list("pk", flat=True))


def tables_in_order(queries):
    """Tabel pertama di tiap query yang membaca atau menghapus, sesuai urutan jalannya."""
    return [re.search(r'FROM "(\w+)"', query["sql"]).group(1) for query in queries if ' FROM "' in query["sql"]]


class UpdateCorrectionServiceTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_complete_product(fiber_100g=None, sodium_100g=0.3976)
        self.correction = submit_correction(
            self.user, self.product, {"brand": "Sarimi Goreng", "fiber_100g": "2,5"}
        )

    def test_full_new_list_replaces_the_items(self):
        old_ids = item_ids(self.correction)
        updated = update_correction(self.user, self.correction, [("fiber_100g", "3"), ("sodium_100g", "500")])
        self.assertEqual(updated.pk, self.correction.pk)
        self.assertEqual((updated.product, updated.submitted_by), (self.product, self.user))
        # brand dihapus, serat diubah, natrium ditambah (diisi 500 mg, disimpan 0.5 g).
        self.assertEqual(stored(updated), {"fiber_100g": (None, "3"), "sodium_100g": ("0.3976", "0.5")})
        self.assertTrue(item_ids(updated).isdisjoint(old_ids))  # item dibuat ulang dengan id baru
        self.assertEqual(DataCorrection.objects.count(), 1)

    def test_old_value_is_read_again_from_the_product(self):
        Product.objects.filter(pk=self.product.pk).update(fiber_100g=1.0)
        updated = update_correction(self.user, self.correction, {"fiber_100g": "3"})
        self.assertEqual(stored(updated), {"fiber_100g": ("1", "3")})

    def test_a_curator_holding_an_old_item_gets_404(self):
        old_item = self.correction.items.get(field_name="fiber_100g")
        update_correction(self.user, self.correction, {"fiber_100g": "3"})
        error = error_of(lambda: approve_item(make_staff(), old_item))
        self.assertEqual((error.error_id, error.status), ("correction_not_found", 404))
        self.product.refresh_from_db()
        self.assertIsNone(self.product.fiber_100g)  # nilai yang belum dilihat kurator tidak tertulis

    def test_only_the_owner_can_update(self):
        before = stored(self.correction)
        for user in (make_user("lain@email.com", "Lain"), AnonymousUser()):
            with self.subTest(user=user):
                error = error_of(lambda: update_correction(user, self.correction, {"fiber_100g": "3"}))
                self.assertEqual((error.error_id, error.status), ("correction_not_found", 404))
        self.assertEqual(stored(self.correction), before)

    def test_reviewed_correction_is_not_editable(self):
        cases = [{"brand": APPROVED}, {"brand": REJECTED}, {"brand": PENDING, "fiber_100g": APPROVED}]
        for statuses in cases:
            with self.subTest(statuses=statuses):
                correction = make_correction(self.product, self.user, **statuses)
                before = item_ids(correction)
                error = error_of(lambda: update_correction(self.user, correction, {"fiber_100g": "3"}))
                self.assertEqual((error.error_id, error.status, error.message),
                                 ("not_editable", 409, NOT_EDITABLE["detail"]))
                self.assertEqual(item_ids(correction), before)

    def test_inactive_product_is_409(self):
        Product.objects.filter(pk=self.product.pk).update(is_active=False)
        error = error_of(lambda: update_correction(self.user, self.correction, {"fiber_100g": "3"}))
        self.assertEqual((error.error_id, error.status), ("product_inactive", 409))

    def test_same_input_rules_as_submitting(self):
        before = stored(self.correction)
        cases = [
            ("kosong", {}, {}),
            ("field ganda", [("brand", "A"), ("brand", "B")], {"brand": [DUPLICATE_MESSAGE]}),
            ("field terlarang", {"code": "8991234567890"}, {"code": [FORBIDDEN_MESSAGE]}),
            ("nova 5", {"nova_group": "5"}, {"nova_group": [NOVA_MESSAGE]}),
            ("sama dengan nilai sekarang", {"brand": "Sarimi"}, {"brand": [MESSAGES["unchanged"]]}),
        ]
        for name, changes, fields in cases:
            with self.subTest(name):
                error = error_of(lambda: update_correction(self.user, self.correction, changes))
                self.assertEqual((error.error_id, error.fields), ("validation_error", fields))
                if not fields:
                    self.assertEqual(error.message, EMPTY_MESSAGE)
        self.assertEqual(stored(self.correction), before)

    def test_locks_correction_then_items_then_product(self):
        with CaptureQueriesContext(connection) as queries:
            update_correction(self.user, self.correction, {"fiber_100g": "3"})
        self.assertEqual(tables_in_order(queries)[:3], [
            DataCorrection._meta.db_table, DataCorrectionItem._meta.db_table, Product._meta.db_table,
        ])


class UpdateCorrectionApiTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_complete_product(
            product_name="Sarimi Isi 2 Goreng", fiber_100g=None, sodium_100g=0.3976
        )
        self.correction = submit_correction(
            self.user, self.product, {"brand": "Sarimi Goreng", "fiber_100g": "2,5"}
        )
        self.client = api_client(self.user)
        self.token = csrf_token(self.client)

    def body(self, *changes):
        """Body PATCH dari pasangan (field_name, proposed_value)."""
        return {"items": [{"field_name": name, "proposed_value": value} for name, value in changes]}

    def patch(self, body, pk=None):
        url = detail_url(pk or self.correction.pk)
        return self.client.patch(url, body, format="json", HTTP_X_CSRFTOKEN=self.token)

    def test_owner_changes_one_proposal(self):
        response = self.patch(self.body(("brand", "Sarimi Goreng"), ("fiber_100g", "3")))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(list(data), CORRECTION_KEYS)
        self.assertEqual(
            (data["id"], data["status"], data["is_withdrawable"], data["product"]["id"]),
            (self.correction.pk, "pending", True, self.product.pk),
        )
        fiber = next(item for item in data["items"] if item["field_name"] == "fiber_100g")
        self.assertEqual((fiber["proposed_value"], fiber["proposed_display"]), (3.0, "3"))
        self.assertEqual(stored(self.correction), {
            "brand": ("Sarimi", "Sarimi Goreng"),
            "fiber_100g": (None, "3"),
        })
        self.assertEqual(data, self.client.get(detail_url(self.correction.pk)).json())  # sama dengan GET

    def test_body_is_the_full_new_list(self):
        old_ids = item_ids(self.correction)
        response = self.patch(self.body(("sodium_100g", "500")))
        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertEqual([item["field_name"] for item in items], ["sodium_100g"])  # brand dan serat dihapus
        sodium = items[0]
        self.assertEqual(
            (sodium["old_value"], sodium["proposed_value"], sodium["old_display"], sodium["proposed_display"]),
            (0.3976, 0.5, "397,6", "500"),
        )
        self.assertNotIn(sodium["id"], old_ids)
        # Field yang belum ada di pengajuan boleh ditambah; urutan item mengikuti CORRECTABLE_FIELDS.
        response = self.patch(self.body(("sodium_100g", "500"), ("brand", "Sarimi Goreng")))
        self.assertEqual([item["field_name"] for item in response.json()["items"]], ["brand", "sodium_100g"])

    def test_product_cannot_be_changed(self):
        other = make_complete_product(fiber_100g=None)
        response = self.patch({**self.body(("fiber_100g", "3")), "product": other.pk})
        self.assertEqual((response.status_code, response.json()["product"]["id"]), (200, self.product.pk))
        self.correction.refresh_from_db()
        self.assertEqual(self.correction.product_id, self.product.pk)

    def test_reviewed_correction_is_409_not_editable(self):
        cases = [{"brand": APPROVED}, {"brand": REJECTED}, {"brand": PENDING, "fiber_100g": APPROVED}]
        for statuses in cases:
            with self.subTest(statuses=statuses):
                correction = make_correction(self.product, self.user, **statuses)
                before = stored(correction)
                response = self.patch(self.body(("fiber_100g", "3")), correction.pk)
                self.assertEqual((response.status_code, response.json()), (409, NOT_EDITABLE))
                self.assertEqual(stored(correction), before)

    def test_someone_elses_or_missing_is_404(self):
        theirs = make_correction(self.product, make_user("lain@email.com", "Lain"), brand=PENDING)
        for pk in (theirs.pk, 999999):
            with self.subTest(pk=pk):
                response = self.patch(self.body(("fiber_100g", "3")), pk)
                self.assertEqual((response.status_code, response.json()), (404, NOT_FOUND))
        self.assertEqual(stored(theirs), {"brand": (None, "1")})

    def test_visitor_gets_403(self):
        visitor = api_client()
        response = visitor.patch(
            detail_url(self.correction.pk), self.body(("fiber_100g", "3")), format="json",
            HTTP_X_CSRFTOKEN=csrf_token(visitor),
        )
        self.assertEqual((response.status_code, response.json()), (403, AUTH_REQUIRED))
        self.assertEqual(stored(self.correction)["fiber_100g"], (None, "2.5"))

    def test_without_csrf_token_gets_403(self):
        response = self.client.patch(detail_url(self.correction.pk), self.body(("fiber_100g", "3")), format="json")
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("code", response.json())  # galat bawaan DRF, bukan galat modul
        self.assertEqual(stored(self.correction)["fiber_100g"], (None, "2.5"))

    def test_invalid_input_is_400_with_fields(self):
        before = stored(self.correction)
        cases = [
            ("field ganda", self.body(("brand", "A"), ("brand", "B")), {"brand": [DUPLICATE_MESSAGE]}),
            ("field terlarang", self.body(("code", "8991234567890")), {"code": [FORBIDDEN_MESSAGE]}),
            ("nova 5", self.body(("nova_group", "5")), {"nova_group": [NOVA_MESSAGE]}),
            ("sama dengan nilai sekarang", self.body(("brand", "Sarimi")), {"brand": [MESSAGES["unchanged"]]}),
        ]
        for name, body, fields in cases:
            with self.subTest(name):
                response = self.patch(body)
                self.assertEqual((response.status_code, response.json()), (400, {**INVALID, "fields": fields}))
        response = self.patch(self.body())
        self.assertEqual((response.status_code, response.json()),
                         (400, {"detail": EMPTY_MESSAGE, "code": "validation_error"}))
        for body in ({}, {"items": "brand"}, {"items": [{"proposed_value": "A"}]}):
            with self.subTest(body=body):
                response = self.patch(body)
                data = response.json()
                self.assertEqual((response.status_code, data["code"], list(data["fields"])),
                                 (400, "validation_error", ["items"]))
        self.assertEqual(stored(self.correction), before)

    def test_inactive_product_is_409(self):
        Product.objects.filter(pk=self.product.pk).update(is_active=False)
        response = self.patch(self.body(("fiber_100g", "3")))
        self.assertEqual((response.status_code, response.json()), (409, PRODUCT_INACTIVE))

    def test_withdraw_still_works_after_update(self):
        self.assertEqual(self.patch(self.body(("fiber_100g", "3"))).status_code, 200)
        response = self.client.delete(detail_url(self.correction.pk), HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(DataCorrection.objects.filter(pk=self.correction.pk).exists())

    def test_review_works_on_the_new_items(self):
        old_fiber = self.correction.items.get(field_name="fiber_100g")
        items = self.patch(self.body(("brand", "Sarimi Goreng"), ("fiber_100g", "3"))).json()["items"]
        new = {item["field_name"]: item["id"] for item in items}
        curator = api_client(make_staff())
        token = csrf_token(curator)

        def review(pk, body):
            return curator.patch(item_url(pk), body, format="json", HTTP_X_CSRFTOKEN=token)

        # Kurator yang masih membuka item lama mendapat 404, jadi tidak menyetujui nilai yang belum ia lihat.
        response = review(old_fiber.pk, {"status": "approved"})
        self.assertEqual((response.status_code, response.json()), (404, ITEM_NOT_FOUND))
        self.assertEqual(review(new["fiber_100g"], {"status": "approved"}).status_code, 200)
        response = review(new["brand"], {"status": "rejected", "review_note": "Tidak sesuai label."})
        self.assertEqual(response.json()["correction"]["status"], "partial")
        self.product.refresh_from_db()
        self.assertEqual((self.product.fiber_100g, self.product.brand), (3.0, "Sarimi"))
        # Setelah ditinjau, pengajuan tidak bisa diubah lagi.
        response = self.patch(self.body(("fiber_100g", "4")))
        self.assertEqual((response.status_code, response.json()), (409, NOT_EDITABLE))
