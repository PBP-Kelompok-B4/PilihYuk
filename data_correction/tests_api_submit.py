"""Tes API DRF Modul 4: GET products/<pk>/form/ dan POST mine/ (ajukan koreksi).

Notes:
- Klien dari api_fixtures: APIClient(enforce_csrf_checks=True) + force_login, token CSRF dari
  halaman Browsable API (pola Tutorial 07).
- Helper data dan pesan diimpor sebagai fungsi/konstanta dari tests.py, bukan kelas TestCase.
- Produk uji: lengkap kecuali serat (kosong), natrium 0.3976 g (tampil 397,6 mg).
"""
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from rest_framework.test import APITestCase

from .api_fixtures import api_client, csrf_token
from .constants import CORRECTABLE_FIELDS
from .models import DataCorrection
from .tests import (
    DUPLICATE_MESSAGE,
    EMPTY_MESSAGE,
    FORBIDDEN_MESSAGE,
    NOVA_MESSAGE,
    SEPARATOR_MESSAGE,
    make_complete_product,
    make_user,
)
from .validators import MESSAGES

MINE_URL = "/api/v1/corrections/mine/"
INVALID = {"detail": "Periksa kembali isian koreksi.", "code": "validation_error"}
NOT_FOUND = {"detail": "Produk tidak ditemukan.", "code": "product_not_found"}

PRODUCT_KEYS = ["id", "product_name", "brand", "quantity", "image_url", "is_active"]
FIELD_KEYS = [
    "field_name", "label", "group", "type", "current_value", "current_display", "display_factor",
    "help_text",
]
CORRECTION_KEYS = ["id", "product", "status", "status_label", "is_withdrawable", "created_at", "items"]
ITEM_KEYS = [
    "id", "field_name", "label", "old_value", "proposed_value", "old_display", "proposed_display",
    "status", "status_label", "review_note",
]


def form_url(pk):
    return reverse("data_correction_api:correction_form", args=[pk])


class SubmitApiTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_complete_product(
            product_name="Sarimi Isi 2 Goreng", fiber_100g=None, sodium_100g=0.3976
        )
        self.client = api_client(self.user)
        self.token = csrf_token(self.client)

    def body(self, *changes, product=None):
        """Body POST dari pasangan (field_name, proposed_value)."""
        return {
            "product": product or self.product.pk,
            "items": [{"field_name": name, "proposed_value": value} for name, value in changes],
        }

    def post(self, body, token=True):
        extra = {"HTTP_X_CSRFTOKEN": self.token} if token else {}
        return self.client.post(MINE_URL, body, format="json", **extra)

    def test_urls_are_stable(self):
        self.assertEqual(form_url(7), "/api/v1/corrections/products/7/form/")
        self.assertEqual(reverse("data_correction_api:my_corrections"), MINE_URL)

    def test_visitor_gets_403_and_nothing_is_saved(self):
        visitor = api_client()
        self.assertEqual(visitor.get(form_url(self.product.pk)).status_code, 403)
        response = visitor.post(MINE_URL, self.body(("fiber_100g", "2,5")), format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(DataCorrection.objects.exists())

    def test_form_lists_fields_with_current_values(self):
        response = self.client.get(form_url(self.product.pk))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(list(data), ["product", "focus", "correctable_fields"])
        self.assertEqual(data["product"], {
            "id": self.product.pk, "product_name": "Sarimi Isi 2 Goreng", "brand": "Sarimi",
            "quantity": "88 g", "image_url": "", "is_active": True,
        })
        self.assertEqual(data["focus"], [])
        rows = data["correctable_fields"]
        self.assertEqual([row["field_name"] for row in rows], list(CORRECTABLE_FIELDS))
        self.assertEqual(list(rows[0]), FIELD_KEYS)
        fields = {row["field_name"]: row for row in rows}
        self.assertEqual(fields["sodium_100g"], {
            "field_name": "sodium_100g", "label": "Natrium (mg/100 g)", "group": "Gizi per 100 g",
            "type": "number", "current_value": 0.3976, "current_display": "397,6",
            "display_factor": 1000,
            "help_text": "Angka dalam mg per 100 g, tanpa pemisah ribuan. Contoh: 780.",
        })
        fiber, nova, brand = fields["fiber_100g"], fields["nova_group"], fields["brand"]
        self.assertEqual((fiber["current_value"], fiber["current_display"], fiber["display_factor"]),
                         (None, None, 1))
        self.assertEqual((nova["type"], nova["group"], nova["current_value"], nova["current_display"]),
                         ("integer", "Tingkat pemrosesan", 4, "4"))
        self.assertEqual((brand["type"], brand["group"], brand["current_value"], brand["current_display"]),
                         ("text", "Info produk", "Sarimi", "Sarimi"))

    def test_form_focus_keeps_known_fields_once(self):
        query = {"field": ["fiber_100g", "code", "fiber_100g", "sodium_100g"]}
        response = self.client.get(form_url(self.product.pk), query)
        self.assertEqual(response.json()["focus"], ["fiber_100g", "sodium_100g"])

    def test_missing_or_inactive_product_is_404(self):
        inactive = make_complete_product(is_active=False)
        for pk in (inactive.pk, 999999):
            with self.subTest(pk=pk):
                response = self.client.get(form_url(pk))
                self.assertEqual((response.status_code, response.json()), (404, NOT_FOUND))
                response = self.post(self.body(("fiber_100g", "2,5"), product=pk))
                self.assertEqual((response.status_code, response.json()), (404, NOT_FOUND))
        self.assertFalse(DataCorrection.objects.exists())

    def test_post_without_csrf_token_is_403(self):
        response = self.post(self.body(("fiber_100g", "2,5")), token=False)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("code", response.json())  # galat bawaan DRF, bukan galat modul
        self.assertFalse(DataCorrection.objects.exists())

    def test_post_creates_correction_for_the_logged_in_user(self):
        other = make_user("lain@email.com", "Lain")
        body = self.body(("sodium_100g", "780"), ("fiber_100g", "2,5"), ("proteins_100g", 8.5))
        body["submitted_by"] = other.pk  # harus diabaikan
        response = self.post(body)
        self.assertEqual(response.status_code, 201)

        correction = DataCorrection.objects.get()
        self.assertEqual((correction.submitted_by, correction.product), (self.user, self.product))
        stored = {item.field_name: (item.old_value, item.proposed_value) for item in correction.items.all()}
        self.assertEqual(stored, {
            "proteins_100g": ("8", "8.5"),
            "fiber_100g": (None, "2.5"),
            "sodium_100g": ("0.3976", "0.78"),  # diisi 780 mg, disimpan 0.78 g
        })

        data = response.json()
        self.assertEqual(list(data), CORRECTION_KEYS)
        self.assertEqual(list(data["product"]), PRODUCT_KEYS)
        self.assertEqual(
            (data["id"], data["status"], data["status_label"], data["is_withdrawable"]),
            (correction.pk, "pending", "Menunggu", True),
        )
        self.assertEqual(parse_datetime(data["created_at"]), correction.created_at)
        # Urutan item mengikuti CORRECTABLE_FIELDS, bukan urutan di body.
        self.assertEqual([item["field_name"] for item in data["items"]],
                         ["proteins_100g", "fiber_100g", "sodium_100g"])
        proteins, fiber, sodium = data["items"]
        self.assertEqual(list(sodium), ITEM_KEYS)
        self.assertEqual(sodium, {
            "id": correction.items.get(field_name="sodium_100g").pk, "field_name": "sodium_100g",
            "label": "Natrium (mg/100 g)", "old_value": 0.3976, "proposed_value": 0.78,
            "old_display": "397,6", "proposed_display": "780",
            "status": "pending", "status_label": "Menunggu", "review_note": "",
        })
        self.assertEqual((fiber["old_value"], fiber["old_display"], fiber["proposed_value"], fiber["proposed_display"]),
                         (None, None, 2.5, "2,5"))
        self.assertEqual((proteins["old_value"], proteins["proposed_value"]), (8.0, 8.5))

    def test_invalid_values_return_400_with_messages_per_field(self):
        cases = [
            ("field terlarang", self.body(("code", "8991234567890"), ("nutrition_grade", "a")),
             {"code": [FORBIDDEN_MESSAGE], "nutrition_grade": [FORBIDDEN_MESSAGE]}),
            ("field ganda", self.body(("brand", "A"), ("brand", "B")), {"brand": [DUPLICATE_MESSAGE]}),
            ("nova 5", self.body(("nova_group", "5")), {"nova_group": [NOVA_MESSAGE]}),
            ("gizi negatif", self.body(("fat_100g", "-1")), {"fat_100g": [MESSAGES["negative"]]}),
            ("pemisah ribuan", self.body(("energy_kcal_100g", "1.234,5")),
             {"energy_kcal_100g": [SEPARATOR_MESSAGE]}),
            ("sama dengan nilai sekarang", self.body(("brand", "Sarimi")), {"brand": [MESSAGES["unchanged"]]}),
        ]
        for name, body, fields in cases:
            with self.subTest(name):
                response = self.post(body)
                self.assertEqual((response.status_code, response.json()), (400, {**INVALID, "fields": fields}))
        self.assertFalse(DataCorrection.objects.exists())

    def test_empty_items_is_rejected_by_the_service(self):
        response = self.post(self.body())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": EMPTY_MESSAGE, "code": "validation_error"})
        self.assertFalse(DataCorrection.objects.exists())

    def test_malformed_body_returns_400_with_shape_messages(self):
        product = self.product.pk
        cases = [
            ("items bukan daftar", {"product": product, "items": "brand"}, "items"),
            ("baris tanpa field_name", {"product": product, "items": [{"proposed_value": "A"}]}, "items"),
            ("tanpa product", {"items": [{"field_name": "brand", "proposed_value": "A"}]}, "product"),
            ("product bukan angka", {"product": "tujuh", "items": []}, "product"),
        ]
        for name, body, key in cases:
            with self.subTest(name):
                response = self.post(body)
                data = response.json()
                self.assertEqual(response.status_code, 400)
                self.assertEqual((data["detail"], data["code"], list(data["fields"])),
                                 (INVALID["detail"], "validation_error", [key]))
                self.assertTrue(data["fields"][key])
                self.assertTrue(all(isinstance(message, str) for message in data["fields"][key]))
        response = self.post({"product": product, "items": [{"proposed_value": "A"}]})
        self.assertEqual(response.json()["fields"]["items"], ["Baris 1, field_name: Bidang ini harus diisi."])
        self.assertFalse(DataCorrection.objects.exists())