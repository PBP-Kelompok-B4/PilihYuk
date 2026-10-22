"""Tes Modul 4 (Antrean Data).

Tahap 2: model, constraint, status turunan, system check, dan admin. Helper membuat data
seperti aslinya: username berisi email huruf kecil dan nama tampilan di first_name
(keputusan 38). Product cukup diisi `source`, satu-satunya field wajib tanpa nilai bawaan
(temuan Tahap 0), ditambah barcode 13 digit yang unik dan nama produk.

Notes:
- Cara menjalankan: `python manage.py test data_correction`
- Django membuat database tes sementara yang kosong, lalu
  menghapusnya setelah selesai. Data asli tidak tersentuh.
- TestCase       : tes yang memakai database. Setiap tes dibungkus transaksi yang
                   dibatalkan di akhir, jadi data satu tes tidak bocor ke tes lain.
- SimpleTestCase : tes tanpa database (lebih cepat), untuk konstanta dan system check.
- setUp()        : dijalankan sebelum SETIAP method test_... di kelas itu.
- subTest()      : menjalankan beberapa kasus dalam satu tes. Kalau satu kasus gagal,
                   laporan menyebut kasus yang mana, dan kasus lain tetap diuji.
- Isi file:
  1. DataCorrectionModelTests : model, constraint, dan efek on_delete
  2. DerivedStatusTests       : status turunan dan is_withdrawable
  3. ConstantsTests           : isi constants.py sesuai PRD
  4. SystemCheckTests         : checks.py menangkap ketidakcocokan
  5. AdminTests               : admin hanya-baca dan tidak membocorkan email
"""
import json
from itertools import count
from unittest import mock

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.checks.registry import registry
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from django import forms
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import models
from django.http import HttpResponse
from django.test import RequestFactory
from django.contrib.messages import get_messages
from django.db import connection
from django.http import QueryDict
from django.template import Context, Template
from django.test.utils import CaptureQueriesContext
from django.utils.dateparse import parse_datetime

from product_catalog.models import Product

from . import constants
from .checks import check_correctable_fields
from .constants import APPROVED, CORRECTION_STATUS_LABELS, PARTIAL, PENDING, REJECTED
from .models import DataCorrection, DataCorrectionItem
from .incomplete import incomplete_products, missing_count, missing_data
from .responses import (
    field_errors,
    json_error,
    json_ok,
    login_required_json,
    page_payload,
    render_or_json,
    staff_required,
    wants_json,
)
from .services import CorrectionError, approve_item, reject_item, submit_correction, withdraw_correction
from .validators import get_current_value, parse_proposed_value, to_column_value, to_display, to_stored_text
from .forms import CorrectionForm, help_text_for
from .templatetags.data_correction_tags import display_value

_barcodes = count(1)


def make_user(email="pengaju@email.com", name="Budi", **extra):
    # password=None: akun tidak bisa dipakai masuk lewat form. Tes memakai force_login,
    # dan hashing password asli membuat setiap tes jauh lebih lambat.
    email = email.lower()
    return get_user_model().objects.create_user(
        username=email, email=email, password=None, first_name=name, **extra
    )


def make_staff(email="kurator@email.com", name="Kurator", **extra):
    return make_user(email, name, is_staff=True, **extra)


def make_product(**fields):
    number = next(_barcodes)
    data = {"code": f"899{number:010d}", "product_name": f"Produk Uji {number}", "source": "off"}
    data.update(fields)
    return Product.objects.create(**data)


def make_correction(product, user, **statuses):
    """Pengajuan dengan satu item per field, misalnya make_correction(p, u, brand=PENDING)."""
    correction = DataCorrection.objects.create(product=product, submitted_by=user)
    for field_name, status in statuses.items():
        DataCorrectionItem.objects.create(
            correction=correction, field_name=field_name, proposed_value="1", status=status
        )
    return correction


class DataCorrectionModelTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product()

    def test_create_correction_with_items(self):
        correction = DataCorrection.objects.create(product=self.product, submitted_by=self.user)
        DataCorrectionItem.objects.create(correction=correction, field_name="brand", proposed_value="Sarimi")
        DataCorrectionItem.objects.create(
            correction=correction, field_name="sodium_100g", old_value="0.3976", proposed_value="0.4"
        )

        brand, sodium = correction.items.all()  # urutan sama dengan urutan dibuat
        self.assertEqual((brand.field_name, sodium.field_name), ("brand", "sodium_100g"))
        self.assertEqual((brand.status, brand.review_note), (PENDING, ""))
        self.assertIsNone(brand.old_value)  # NULL berarti tidak diketahui
        self.assertEqual(sodium.old_value, "0.3976")  # satuan kolom: gram
        self.assertIsNotNone(correction.created_at)
        self.assertIsNone(correction.reviewed_by)
        self.assertIsNone(correction.reviewed_at)
        self.assertEqual(list(self.product.data_corrections.all()), [correction])
        self.assertEqual(list(self.user.submitted_data_corrections.all()), [correction])

    def test_same_field_twice_in_one_correction_is_rejected(self):
        correction = make_correction(self.product, self.user, brand=PENDING)
        with self.assertRaises(IntegrityError), transaction.atomic():
            DataCorrectionItem.objects.create(
                correction=correction, field_name="brand", proposed_value="Lain"
            )
        self.assertEqual(correction.items.count(), 1)

    def test_same_field_in_different_corrections_is_allowed(self):
        make_correction(self.product, self.user, brand=PENDING)
        make_correction(self.product, self.user, brand=PENDING)
        make_correction(self.product, make_user("sari@email.com", "Sari"), brand=PENDING)
        make_correction(make_product(), self.user, brand=PENDING)
        self.assertEqual(DataCorrectionItem.objects.filter(field_name="brand").count(), 4)

    def test_deleting_product_with_correction_is_protected(self):
        make_correction(self.product, self.user, brand=PENDING)
        with self.assertRaises(ProtectedError):
            self.product.delete()
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

        unused = make_product()
        unused.delete()  # tanpa pengajuan, PROTECT tidak menghalangi
        self.assertFalse(Product.objects.filter(pk=unused.pk).exists())

    def test_catalog_soft_delete_refuses_product_with_correction(self):
        # K-1: product_delete di katalog memeriksa semua relasi PROTECT, termasuk relasi ini.
        manual = make_product(code=None, source="manual", added_by=self.user)
        make_correction(manual, make_user("sari@email.com", "Sari"), brand=PENDING)
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("product_catalog:product_delete", args=[manual.pk]), HTTP_ACCEPT="application/json"
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["id"], "product_in_use")
        manual.refresh_from_db()
        self.assertTrue(manual.is_active)

    def test_field_outside_fixed_list_is_rejected_by_database(self):
        correction = make_correction(self.product, self.user)
        forbidden = ("code", "added_by", "source", "nutrition_grade", "image_url", "misc_tags", "is_active")
        for field_name in forbidden:
            with self.subTest(field_name=field_name):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    DataCorrectionItem.objects.create(
                        correction=correction, field_name=field_name, proposed_value="x"
                    )

    def test_unknown_status_is_rejected_by_database(self):
        correction = make_correction(self.product, self.user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            DataCorrectionItem.objects.create(
                correction=correction, field_name="brand", proposed_value="x", status="withdrawn"
            )

    def test_full_clean_follows_choices_and_required_value(self):
        correction = make_correction(self.product, self.user)
        DataCorrectionItem(correction=correction, field_name="brand", proposed_value="Sarimi").full_clean()
        for field_name, proposed_value in (("code", "1"), ("brand", "")):
            with self.subTest(field_name=field_name, proposed_value=proposed_value):
                with self.assertRaises(ValidationError):
                    DataCorrectionItem(
                        correction=correction, field_name=field_name, proposed_value=proposed_value
                    ).full_clean()

    def test_deleting_submitter_deletes_corrections_and_items(self):
        make_correction(self.product, self.user, brand=PENDING, origin=APPROVED)
        self.user.delete()
        self.assertFalse(DataCorrection.objects.exists())
        self.assertFalse(DataCorrectionItem.objects.exists())

    def test_deleting_reviewer_keeps_correction(self):
        curator = make_staff()
        correction = make_correction(self.product, self.user, brand=APPROVED)
        correction.reviewed_by = curator
        correction.reviewed_at = timezone.now()
        correction.save()

        curator.delete()
        correction.refresh_from_db()
        self.assertIsNone(correction.reviewed_by)
        self.assertIsNotNone(correction.reviewed_at)
        self.assertEqual(correction.items.count(), 1)

    def test_deleting_correction_deletes_items_only(self):
        correction = make_correction(self.product, self.user, brand=PENDING, origin=PENDING)
        correction.delete()  # sama dengan tarik pengajuan
        self.assertFalse(DataCorrectionItem.objects.exists())
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_str_and_labels(self):
        correction = make_correction(self.product, self.user, sodium_100g=PENDING)
        item = correction.items.get()
        self.assertEqual(item.get_field_name_display(), "Natrium (mg/100 g)")
        self.assertEqual(str(correction), f"Koreksi #{correction.pk} · {self.product.product_name}")
        self.assertEqual(str(item), f"Koreksi #{correction.pk} · Natrium (mg/100 g) · Menunggu")
        self.assertEqual(str(DataCorrection()), "Koreksi baru")
        nameless = make_correction(make_product(product_name=""), self.user)
        self.assertEqual(str(nameless), f"Koreksi #{nameless.pk} · produk #{nameless.product_id}")


class DerivedStatusTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product()

    def test_status_and_withdrawable_for_item_combinations(self):
        cases = [
            ({}, PENDING, True),
            ({"brand": PENDING}, PENDING, True),
            ({"brand": PENDING, "origin": PENDING}, PENDING, True),
            ({"brand": APPROVED, "origin": PENDING}, PENDING, False),
            ({"brand": REJECTED, "origin": PENDING}, PENDING, False),
            ({"brand": APPROVED, "origin": REJECTED, "quantity": PENDING}, PENDING, False),
            ({"brand": APPROVED}, APPROVED, False),
            ({"brand": APPROVED, "origin": APPROVED}, APPROVED, False),
            ({"brand": REJECTED}, REJECTED, False),
            ({"brand": REJECTED, "origin": REJECTED}, REJECTED, False),
            ({"brand": APPROVED, "origin": REJECTED}, PARTIAL, False),
        ]
        for statuses, expected, withdrawable in cases:
            with self.subTest(statuses=statuses):
                correction = make_correction(self.product, self.user, **statuses)
                self.assertEqual(correction.status, expected)
                self.assertEqual(correction.get_status_display(), CORRECTION_STATUS_LABELS[expected])
                self.assertIs(correction.is_withdrawable, withdrawable)

    def test_status_follows_review_on_same_instance(self):
        correction = make_correction(self.product, self.user, brand=PENDING, origin=PENDING)
        self.assertTrue(correction.is_withdrawable)
        correction.items.filter(field_name="brand").update(status=APPROVED)
        self.assertEqual(correction.status, PENDING)
        self.assertFalse(correction.is_withdrawable)
        correction.items.filter(field_name="origin").update(status=REJECTED)
        self.assertEqual(correction.status, PARTIAL)
        self.assertEqual(correction.get_status_display(), "Sebagian disetujui")

    def test_unsaved_correction_is_pending(self):
        correction = DataCorrection(product=self.product, submitted_by=self.user)
        self.assertEqual(correction.status, PENDING)
        self.assertTrue(correction.is_withdrawable)

    def test_status_uses_prefetched_items(self):
        for _ in range(3):
            make_correction(self.product, self.user, brand=APPROVED, origin=PENDING)
        with self.assertNumQueries(2):
            rows = [
                (correction.status, correction.is_withdrawable, correction.get_status_display())
                for correction in DataCorrection.objects.prefetch_related("items")
            ]
        self.assertEqual(rows, [(PENDING, False, "Menunggu")] * 3)


class ConstantsTests(SimpleTestCase):
    def test_correctable_fields_follow_prd(self):
        self.assertEqual(constants.CORRECTABLE_FIELDS, (
            "product_name", "brand", "quantity", "category", "origin", "nova_group",
            "energy_kcal_100g", "proteins_100g", "fat_100g", "saturated_fat_100g",
            "carbohydrates_100g", "sugars_100g", "fiber_100g", "sodium_100g",
        ))
        forbidden = (
            "code", "added_by", "source", "nutrition_grade", "environmental_grade",
            "environmental_grade_estimated", "image_url", "misc_tags", "halal_labeled", "is_active",
        )
        for field_name in forbidden:
            self.assertNotIn(field_name, constants.CORRECTABLE_FIELDS)

    def test_labels_units_and_statuses(self):
        self.assertEqual([name for name, _ in constants.FIELD_CHOICES], list(constants.CORRECTABLE_FIELDS))
        self.assertEqual(constants.INTEGER_FIELDS, ("nova_group",))
        self.assertEqual(constants.FIELD_LABELS["energy_kcal_100g"], "Energi (kkal/100 g)")
        self.assertEqual(constants.FIELD_LABELS["sodium_100g"], "Natrium (mg/100 g)")
        self.assertEqual(constants.DISPLAY_FACTORS, {"sodium_100g": 1000})
        self.assertEqual(
            dict(constants.STATUS_CHOICES),
            {PENDING: "Menunggu", APPROVED: "Disetujui", REJECTED: "Ditolak"},
        )
        self.assertEqual(CORRECTION_STATUS_LABELS[PARTIAL], "Sebagian disetujui")


class SystemCheckTests(SimpleTestCase):
    def error_ids(self, **kwargs):
        return [error.id for error in check_correctable_fields(**kwargs)]

    def test_check_is_registered_and_passes(self):
        self.assertIn(check_correctable_fields, registry.get_checks())
        self.assertEqual(check_correctable_fields(), [])

    def test_field_missing_from_product_fails(self):
        with (
            mock.patch.object(constants, "CORRECTABLE_FIELDS", constants.CORRECTABLE_FIELDS + ("salt_100g",)),
            mock.patch.object(constants, "NUTRITION_FIELDS", constants.NUTRITION_FIELDS + ("salt_100g",)),
            mock.patch.dict(constants.FIELD_LABELS, {"salt_100g": "Garam (g/100 g)"}),
        ):
            self.assertEqual(self.error_ids(), ["data_correction.E003"])

    def test_wrong_column_type_fails(self):
        with (
            mock.patch.object(constants, "TEXT_FIELDS", constants.TEXT_FIELDS + ("nova_group",)),
            mock.patch.object(constants, "INTEGER_FIELDS", ()),
        ):
            self.assertEqual(self.error_ids(), ["data_correction.E004"])

    def test_inconsistent_constants_fail(self):
        patchers = {
            "field tanpa kelompok": mock.patch.object(constants, "INTEGER_FIELDS", ()),
            "label berlebih": mock.patch.dict(constants.FIELD_LABELS, {"code": "Barcode"}),
            "faktor untuk teks": mock.patch.dict(constants.DISPLAY_FACTORS, {"brand": 2}),
        }
        for case, patcher in patchers.items():
            with self.subTest(case=case), patcher:
                self.assertEqual(self.error_ids(), ["data_correction.E001"])

    def test_missing_product_model_fails(self):
        with mock.patch.object(apps, "get_model", side_effect=LookupError):
            self.assertEqual(self.error_ids(), ["data_correction.E002"])

    def test_only_runs_when_this_app_is_checked(self):
        catalog = apps.get_app_config("product_catalog")
        mine = apps.get_app_config("data_correction")
        with mock.patch.object(constants, "INTEGER_FIELDS", ()):
            self.assertEqual(self.error_ids(app_configs=[catalog]), [])
            self.assertEqual(self.error_ids(app_configs=[catalog, mine]), ["data_correction.E001"])


class AdminTests(TestCase):
    """Admin hanya untuk debug: hanya-baca, dan tidak pernah menampilkan username atau email."""

    def setUp(self):
        self.correction = make_correction(
            make_product(product_name="Sarimi Isi 2 Goreng"), make_user(), brand=APPROVED, origin=REJECTED
        )
        self.correction.reviewed_by = make_staff(name="")  # tanpa first_name
        self.correction.save()
        self.item = self.correction.items.first()
        self.client.force_login(
            get_user_model().objects.create_superuser("admin@email.com", "admin@email.com", None)
        )

    def test_pages_render_without_username_or_email(self):
        changelist = reverse("admin:data_correction_datacorrection_changelist")
        item_changelist = reverse("admin:data_correction_datacorrectionitem_changelist")
        urls = (
            reverse("admin:app_list", kwargs={"app_label": "data_correction"}),
            changelist,
            changelist + "?items__status__exact=approved",
            reverse("admin:data_correction_datacorrection_change", args=[self.correction.pk]),
            item_changelist + "?status__exact=rejected",
            reverse("admin:data_correction_datacorrectionitem_change", args=[self.item.pk]),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "pengaju@email.com")
                self.assertNotContains(response, "kurator@email.com")

        make_correction(make_product(), make_user("sari@email.com", "Sari"), brand=PENDING)  # belum ditinjau
        response = self.client.get(changelist)
        self.assertContains(response, '<td class="field-submitter">Budi</td>', html=True)
        self.assertContains(response, '<td class="field-reviewer">Pengguna</td>', html=True)
        self.assertContains(response, '<td class="field-reviewer">-</td>', html=True)
        self.assertContains(response, '<td class="field-status_label">Sebagian disetujui</td>', html=True)
        self.assertContains(response, "Sarimi Isi 2 Goreng")

    def test_admin_cannot_add_or_change(self):
        add_urls = (
            "admin:data_correction_datacorrection_add",
            "admin:data_correction_datacorrectionitem_add",
        )
        for name in add_urls:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        change = reverse("admin:data_correction_datacorrection_change", args=[self.correction.pk])
        self.assertEqual(self.client.post(change, {}).status_code, 403)
        item_change = reverse("admin:data_correction_datacorrectionitem_change", args=[self.item.pk])
        self.assertEqual(self.client.post(item_change, {"status": PENDING}).status_code, 403)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, APPROVED)

    def test_admin_can_delete_correction(self):
        url = reverse("admin:data_correction_datacorrection_delete", args=[self.correction.pk])
        self.assertEqual(self.client.post(url, {"post": "yes"}).status_code, 302)
        self.assertFalse(DataCorrection.objects.exists())
        self.assertFalse(DataCorrectionItem.objects.exists())


COMPLETE_FIELDS = {
    "brand": "Sarimi", "quantity": "88 g", "category": "Mi instan", "origin": "Indonesia",
    "nova_group": 4, "energy_kcal_100g": 460.0, "proteins_100g": 8.0, "fat_100g": 19.0,
    "saturated_fat_100g": 9.0, "carbohydrates_100g": 63.0, "sugars_100g": 4.0,
    "fiber_100g": 2.0, "sodium_100g": 0.78,
}
NUMBER_MESSAGE = "Masukkan angka, misalnya 7,5."
SEPARATOR_MESSAGE = "Tulis angka tanpa pemisah ribuan, misalnya 1234,5 (bukan 1.234,5)."
NOVA_MESSAGE = "Grup NOVA harus bilangan bulat 1 sampai 4."


def make_complete_product(**fields):
    """Produk tanpa data kosong; ganti kolom lewat argumen untuk menguji deteksi."""
    return make_product(**{**COMPLETE_FIELDS, **fields})


def error_of(action):
    """Jalankan aksi yang harus gagal, kembalikan CorrectionError-nya."""
    try:
        action()
    except CorrectionError as error:
        return error
    raise AssertionError("CorrectionError tidak terjadi")


class ValidatorTests(SimpleTestCase):
    def assertAccepted(self, field_name, raw, expected, **kwargs):
        value, error = parse_proposed_value(field_name, raw, **kwargs)
        self.assertIsNone(error, f"{field_name}={raw!r}")
        self.assertEqual(value, expected)
        self.assertIs(type(value), type(expected))

    def assertRejected(self, field_name, raw, message, **kwargs):
        with self.subTest(field_name=field_name, raw=raw):
            self.assertEqual(parse_proposed_value(field_name, raw, **kwargs), (None, message))

    def test_current_value_as_text(self):
        product = Product(
            brand="Sarimi", quantity="", origin="  ", nova_group=3, sodium_100g=0.3976,
            fiber_100g=0.0, energy_kcal_100g=64.7058823529412, proteins_100g=None,
        )
        expected = {
            "brand": "Sarimi", "quantity": None, "origin": None, "nova_group": "3",
            "sodium_100g": "0.3976", "fiber_100g": "0", "energy_kcal_100g": "64.7058823529412",
            "proteins_100g": None,
        }
        for field_name, value in expected.items():
            with self.subTest(field_name=field_name):
                self.assertEqual(get_current_value(product, field_name), value)
        with self.assertRaises(ValueError):
            get_current_value(product, "code")

    def test_forbidden_fields(self):
        for field_name in ("code", "nutrition_grade", "environmental_grade", "added_by", "source",
                           "image_url", "misc_tags", "is_active", "halal_labeled"):
            self.assertRejected(field_name, "1", "Field ini tidak boleh dikoreksi.")

    def test_text_rules(self):
        self.assertAccepted("brand", "  Sarimi \n Goreng ", "Sarimi Goreng")
        self.assertAccepted("quantity", 85, "85")
        self.assertAccepted("category", "Mi instan", "Mi instan")  # CharField biasa, tanpa choices
        for raw in ("", "   ", None):
            self.assertRejected("brand", raw, "Isian ini wajib diisi.")
        for raw in (True, ["Sarimi"]):
            self.assertRejected("brand", raw, "Nilai ini tidak valid.")
        limit = Product._meta.get_field("quantity").max_length
        self.assertAccepted("quantity", "x" * limit, "x" * limit)
        too_long = f"Maksimal {limit} karakter (sekarang {limit + 1})."
        self.assertRejected("quantity", "x" * (limit + 1), too_long)

    def test_text_choices_are_enforced_if_a_column_gets_them(self):
        column = models.CharField(max_length=20, choices=[("mi", "Mi"), ("susu", "Susu")])
        with mock.patch.object(Product._meta, "get_field", return_value=column):
            self.assertAccepted("category", "susu", "susu")
            self.assertRejected("category", "teh", "Pilih salah satu nilai yang tersedia.")

    def test_nova_rules(self):
        for raw, expected in (("1", 1), ("4", 4), (" 3 ", 3), (2, 2), (3.0, 3)):
            self.assertAccepted("nova_group", raw, expected)
        for raw in ("0", "5", "2.5", "2,5", "abc", "-1", "1e1", 2.5, True, [3]):
            self.assertRejected("nova_group", raw, NOVA_MESSAGE)
        self.assertRejected("nova_group", "", "Isian ini wajib diisi.")

    def test_number_rules(self):
        accepted = (("7,5", 7.5), ("7.5", 7.5), ("0", 0.0), ("0,0", 0.0), ("-0", 0.0), (",5", 0.5),
                    ("100", 100.0), (" 12,125 ", 12.125), (7.5, 7.5), (0, 0.0))
        for raw, expected in accepted:
            self.assertAccepted("fat_100g", raw, expected)
        rejected = {
            "-1": "Nilai tidak boleh negatif.",
            "-0,5": "Nilai tidak boleh negatif.",
            "1.234,5": SEPARATOR_MESSAGE,
            "1,234.5": SEPARATOR_MESSAGE,
            "abc": NUMBER_MESSAGE,
            "nan": NUMBER_MESSAGE,
            "inf": NUMBER_MESSAGE,
            "Infinity": NUMBER_MESSAGE,
            "1e2": NUMBER_MESSAGE,
            "7,5 g": NUMBER_MESSAGE,
            "1,2,3": NUMBER_MESSAGE,
            "100,5": "Nilai maksimal 100 g per 100 g.",
            "7,1234": "Gunakan paling banyak 3 angka di belakang koma.",
            "": "Isian ini wajib diisi.",
        }
        for raw, message in rejected.items():
            self.assertRejected("fat_100g", raw, message)
        for raw in (float("nan"), float("inf"), True, [1]):
            self.assertRejected("fat_100g", raw, NUMBER_MESSAGE)

    def test_energy_and_sodium_limits(self):
        self.assertAccepted("energy_kcal_100g", "900", 900.0)
        self.assertRejected("energy_kcal_100g", "900,1", "Nilai maksimal 900 kkal per 100 g.")
        self.assertAccepted("sodium_100g", "100000", 100.0)
        self.assertRejected("sodium_100g", "100001", "Nilai maksimal 100000 mg per 100 g.")

    def test_sodium_is_entered_in_mg_and_stored_in_grams(self):
        value, error = parse_proposed_value("sodium_100g", "780")
        self.assertEqual((value, error), (0.78, None))
        self.assertEqual(to_stored_text("sodium_100g", value), "0.78")  # tanpa ekor float
        self.assertAccepted("sodium_100g", "397,6", 0.3976)
        smallest, _ = parse_proposed_value("sodium_100g", "0,001")
        self.assertEqual(to_stored_text("sodium_100g", smallest), "0.000001")
        # Saat persetujuan, teks simpanan sudah dalam gram dan tidak dibagi lagi.
        self.assertAccepted("sodium_100g", "0.78", 0.78, display_units=False)
        self.assertRejected(
            "sodium_100g", "100.5", "Nilai maksimal 100000 mg per 100 g.", display_units=False
        )

    def test_same_as_current_value_is_rejected_after_conversion(self):
        product = Product(brand="Sarimi", sodium_100g=0.78, fat_100g=0.0, nova_group=3, fiber_100g=None)
        same = (("brand", " Sarimi "), ("sodium_100g", "780"), ("fat_100g", "0"), ("nova_group", "3"))
        for field_name, raw in same:
            self.assertRejected(field_name, raw, "Usulan sama dengan nilai saat ini.", product=product)
        self.assertAccepted("brand", "sarimi", "sarimi", product=product)  # beda huruf tetap koreksi
        self.assertAccepted("fiber_100g", "0", 0.0, product=product)  # NULL menjadi 0 adalah perubahan

    def test_stored_column_and_display_conversions(self):
        stored = {("fat_100g", 100.0): "100", ("fat_100g", 0.0): "0", ("brand", "  "): None,
                  ("nova_group", 2): "2", ("fat_100g", None): None}
        for (field_name, value), expected in stored.items():
            with self.subTest(field_name=field_name, value=value):
                self.assertEqual(to_stored_text(field_name, value), expected)
        self.assertEqual(to_column_value("sodium_100g", "0.3976"), 0.3976)
        self.assertEqual(to_column_value("nova_group", "3"), 3)
        self.assertEqual(to_column_value("brand", "Sarimi"), "Sarimi")
        self.assertIsNone(to_column_value("fat_100g", None))
        shown = {("sodium_100g", "0.3976"): "397,6", ("sodium_100g", 0.78): "780",
                 ("energy_kcal_100g", "64.7058823529412"): "64,706", ("fat_100g", "0"): "0",
                 ("nova_group", "3"): "3", ("brand", "Sarimi"): "Sarimi", ("fat_100g", None): None,
                 ("brand", ""): None, ("fat_100g", "rusak"): "rusak"}
        for (field_name, value), expected in shown.items():
            with self.subTest(field_name=field_name, value=value):
                self.assertEqual(to_display(field_name, value), expected)


class SubmitCorrectionTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_complete_product(brand="", sodium_100g=0.3976, fiber_100g=None)

    def test_creates_items_with_old_values_in_fixed_order(self):
        correction = submit_correction(
            self.user, self.product, {"sodium_100g": "780", "brand": " Sarimi ", "fiber_100g": "0"}
        )
        rows = list(correction.items.values_list("field_name", "old_value", "proposed_value", "status"))
        self.assertEqual(rows, [
            ("brand", None, "Sarimi", PENDING),
            ("fiber_100g", None, "0", PENDING),
            ("sodium_100g", "0.3976", "0.78", PENDING),
        ])
        self.assertEqual((correction.product, correction.submitted_by), (self.product, self.user))
        self.product.refresh_from_db()
        self.assertEqual(self.product.brand, "")  # mengajukan belum mengubah Product

    def test_old_value_is_read_from_database(self):
        Product.objects.filter(pk=self.product.pk).update(sodium_100g=0.5)  # instance self.product basi
        correction = submit_correction(self.user, self.product, {"sodium_100g": "780"})
        self.assertEqual(correction.items.get().old_value, "0.5")

    def test_errors_are_reported_per_field_and_nothing_is_saved(self):
        error = error_of(lambda: submit_correction(
            self.user, self.product, {"code": "1", "nova_group": "5", "fat_100g": "7,5", "brand": ""}
        ))
        self.assertEqual((error.error_id, error.status, error.message),
                         ("validation_error", 400, "Periksa kembali isian koreksi."))
        self.assertEqual(error.fields, {
            "code": ["Field ini tidak boleh dikoreksi."],
            "nova_group": [NOVA_MESSAGE],
            "brand": ["Isian ini wajib diisi."],
        })
        self.assertFalse(DataCorrection.objects.exists())

    def test_forbidden_fields_are_rejected(self):
        for field_name in ("code", "nutrition_grade", "added_by", "is_active"):
            with self.subTest(field_name=field_name):
                error = error_of(lambda: submit_correction(self.user, self.product, {field_name: "x"}))
                self.assertEqual(error.fields, {field_name: ["Field ini tidak boleh dikoreksi."]})
        self.assertFalse(DataCorrection.objects.exists())

    def test_duplicate_fields_are_rejected(self):
        changes = [("fat_100g", "7"), ("fat_100g", "8"), ("brand", "Sarimi")]
        error = error_of(lambda: submit_correction(self.user, self.product, changes))
        self.assertEqual(error.fields, {"fat_100g": ["Field ini diajukan lebih dari sekali."]})
        self.assertFalse(DataCorrection.objects.exists())

    def test_empty_changes_are_rejected(self):
        for changes in ({}, [], None):
            with self.subTest(changes=changes):
                error = error_of(lambda: submit_correction(self.user, self.product, changes))
                self.assertEqual(error.message, "Pilih minimal satu field untuk dikoreksi.")

    def test_proposal_equal_to_current_value_is_rejected(self):
        error = error_of(lambda: submit_correction(self.user, self.product, {"sodium_100g": "397,6"}))
        self.assertEqual(error.fields, {"sodium_100g": ["Usulan sama dengan nilai saat ini."]})

    def test_inactive_or_missing_product_is_rejected(self):
        Product.objects.filter(pk=self.product.pk).update(is_active=False)
        error = error_of(lambda: submit_correction(self.user, self.product, {"brand": "Sarimi"}))
        self.assertEqual((error.error_id, error.status), ("product_inactive", 409))
        error = error_of(lambda: submit_correction(self.user, Product(pk=999999), {"brand": "Sarimi"}))
        self.assertEqual((error.error_id, error.status), ("product_not_found", 404))
        self.assertFalse(DataCorrection.objects.exists())

    def test_anonymous_user_is_rejected(self):
        error = error_of(lambda: submit_correction(AnonymousUser(), self.product, {"brand": "Sarimi"}))
        self.assertEqual((error.error_id, error.status), ("authentication_required", 401))


class ReviewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.curator = make_staff()
        self.product = make_complete_product(nova_group=None, sodium_100g=0.3976)
        self.correction = submit_correction(
            self.user, self.product, {"nova_group": "3", "sodium_100g": "780", "brand": "Sarimi Baru"}
        )
        self.items = {item.field_name: item for item in self.correction.items.all()}

    def test_approve_writes_typed_values_and_records_reviewer(self):
        created = Product.objects.get(pk=self.product.pk).updated_at
        result = approve_item(self.curator, self.items["nova_group"])
        self.assertEqual((result.item.status, result.item.review_note, result.stale), (APPROVED, "", False))
        result = approve_item(self.curator, self.items["sodium_100g"], note="  Sesuai label  ")
        self.assertEqual(result.item.review_note, "Sesuai label")

        self.product.refresh_from_db()
        self.assertIs(type(self.product.nova_group), int)
        self.assertEqual(self.product.nova_group, 3)
        self.assertIs(type(self.product.sodium_100g), float)
        self.assertEqual(self.product.sodium_100g, 0.78)
        self.assertEqual(self.product.brand, "Sarimi")  # item brand belum ditinjau
        self.assertGreater(self.product.updated_at, created)
        self.correction.refresh_from_db()
        self.assertEqual(self.correction.reviewed_by, self.curator)
        self.assertIsNotNone(self.correction.reviewed_at)
        self.assertEqual(self.correction.status, PENDING)

    def test_reject_never_touches_product(self):
        before = Product.objects.values().get(pk=self.product.pk)
        result = reject_item(self.curator, self.items["brand"], note="Merek di label tetap Sarimi.")
        self.assertEqual((result.item.status, result.item.review_note, result.stale),
                         (REJECTED, "Merek di label tetap Sarimi.", False))
        self.assertEqual(Product.objects.values().get(pk=self.product.pk), before)
        self.correction.refresh_from_db()
        self.assertEqual(self.correction.reviewed_by, self.curator)

    def test_reject_requires_note(self):
        for note in ("", "   ", None):
            with self.subTest(note=note):
                error = error_of(lambda: reject_item(self.curator, self.items["brand"], note=note))
                self.assertEqual(error.fields, {"review_note": ["Tulis alasan penolakan untuk pengaju."]})
        self.items["brand"].refresh_from_db()
        self.assertEqual(self.items["brand"].status, PENDING)

    def test_double_review_is_rejected(self):
        approve_item(self.curator, self.items["nova_group"])
        for action in (lambda: approve_item(self.curator, self.items["nova_group"]),
                       lambda: reject_item(self.curator, self.items["nova_group"], note="Salah.")):
            error = error_of(action)
            self.assertEqual((error.error_id, error.status), ("already_reviewed", 409))

    def test_non_staff_cannot_review(self):
        for reviewer in (self.user, AnonymousUser()):
            for action in (lambda: approve_item(reviewer, self.items["brand"]),
                           lambda: reject_item(reviewer, self.items["brand"], note="Salah.")):
                error = error_of(action)
                self.assertEqual((error.error_id, error.status), ("forbidden", 403))
        self.product.refresh_from_db()
        self.assertEqual(self.product.brand, "Sarimi")
        self.assertFalse(DataCorrectionItem.objects.exclude(status=PENDING).exists())

    def test_stale_flag_when_product_changed_since_submission(self):
        Product.objects.filter(pk=self.product.pk).update(sodium_100g=0.5)
        result = approve_item(self.curator, self.items["sodium_100g"])
        self.assertTrue(result.stale)
        self.product.refresh_from_db()
        self.assertEqual(self.product.sodium_100g, 0.78)  # tetap ditulis, UI yang memperingatkan

    def test_invalid_stored_value_is_not_written(self):
        DataCorrectionItem.objects.filter(pk=self.items["nova_group"].pk).update(proposed_value="9")
        error = error_of(lambda: approve_item(self.curator, self.items["nova_group"]))
        self.assertEqual(error.fields, {"nova_group": [NOVA_MESSAGE]})
        self.product.refresh_from_db()
        self.assertIsNone(self.product.nova_group)
        self.items["nova_group"].refresh_from_db()
        self.assertEqual(self.items["nova_group"].status, PENDING)

    def test_inactive_product_can_only_be_rejected(self):
        Product.objects.filter(pk=self.product.pk).update(is_active=False)
        error = error_of(lambda: approve_item(self.curator, self.items["brand"]))
        self.assertEqual((error.error_id, error.status), ("product_inactive", 409))
        result = reject_item(self.curator, self.items["brand"], note="Produk sudah nonaktif.")
        self.assertEqual(result.item.status, REJECTED)

    def test_withdrawn_item_cannot_be_reviewed(self):
        withdraw_correction(self.user, self.correction)
        error = error_of(lambda: approve_item(self.curator, self.items["brand"]))
        self.assertEqual((error.error_id, error.status), ("correction_not_found", 404))


class WithdrawCorrectionTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.correction = submit_correction(
            self.user, make_complete_product(brand=""), {"brand": "Sarimi", "fat_100g": "7,5"}
        )

    def test_owner_can_withdraw_while_all_pending(self):
        self.assertEqual(withdraw_correction(self.user, self.correction), self.correction.pk)
        self.assertFalse(DataCorrection.objects.exists())
        self.assertFalse(DataCorrectionItem.objects.exists())

    def test_cannot_withdraw_after_any_review(self):
        reject_item(make_staff(), self.correction.items.get(field_name="brand"), note="Tidak sesuai label.")
        error = error_of(lambda: withdraw_correction(self.user, self.correction))
        self.assertEqual((error.error_id, error.status), ("not_withdrawable", 409))
        self.assertTrue(DataCorrection.objects.filter(pk=self.correction.pk).exists())

    def test_cannot_withdraw_someone_elses(self):
        for other in (make_user("sari@email.com", "Sari"), make_staff(), AnonymousUser()):
            with self.subTest(other=str(other)):
                error = error_of(lambda: withdraw_correction(other, self.correction))
                self.assertEqual((error.error_id, error.status), ("correction_not_found", 404))
        self.assertEqual(DataCorrectionItem.objects.count(), 2)

    def test_second_withdraw_reports_not_found(self):
        withdraw_correction(self.user, self.correction)
        error = error_of(lambda: withdraw_correction(self.user, self.correction))
        self.assertEqual(error.error_id, "correction_not_found")


class IncompleteDataTests(TestCase):
    def summary(self, product):
        return [(entry["key"], entry["correctable"], entry["fields"]) for entry in missing_data(product)]

    def test_complete_product_is_not_listed(self):
        make_complete_product()
        self.assertEqual(incomplete_products(), [])

    def test_unknown_grade_alone_is_not_missing_data(self):
        product = make_complete_product(nutrition_grade="unknown", environmental_grade="unknown")
        self.assertEqual(missing_data(product), [])

    def test_zero_is_not_missing(self):
        product = make_complete_product(**{field: 0.0 for field in constants.NUTRITION_FIELDS})
        self.assertEqual(missing_data(product), [])

    def test_empty_columns_are_detected_without_misc_tags(self):
        product = make_complete_product(
            fiber_100g=None, sodium_100g=None, nova_group=None,
            brand="", quantity="  ", origin="", misc_tags=[],
        )
        self.assertEqual(self.summary(product), [
            ("nutrition", True, ["fiber_100g", "sodium_100g"]),
            ("nova", True, ["nova_group"]),
            ("brand", True, ["brand"]),
            ("quantity", True, ["quantity"]),
            ("origin", True, ["origin"]),
        ])
        labels = [entry["label"] for entry in missing_data(product)]
        self.assertEqual(labels, ["Gizi", "NOVA", "Merek", "Isi bersih", "Asal"])

    def test_prd_tags_add_info_categories(self):
        tags = [
            "en:packagings-not-complete", "en:environmental-score-not-computed",
            "en:nutriscore-missing-prepared-nutrition-data", "en:nutriscore-not-computed",
            "en:packagings-not-empty",  # tag lain diabaikan
        ]
        self.assertEqual(self.summary(make_complete_product(misc_tags=tags)), [
            ("nutrition", False, []),
            ("prepared_nutrition", False, []),
            ("green_score", False, []),
            ("packaging", False, []),
        ])

    def test_nutriscore_tag_with_empty_nutrients_is_correctable(self):
        product = make_complete_product(misc_tags=["en:nutriscore-not-computed"], fiber_100g=None)
        self.assertEqual(self.summary(product), [("nutrition", True, ["fiber_100g"])])

    def test_field_tags_count_only_while_column_is_empty(self):
        tags = [
            "en:nutriscore-missing-nutrition-data-sodium", "en:nutriscore-missing-fiber",
            "en:environmental-score-missing-data-origins", "en:nutriscore-missing-category",
        ]
        self.assertEqual(missing_data(make_complete_product(misc_tags=tags)), [])  # sudah dilengkapi
        empty = make_complete_product(
            misc_tags=tags, sodium_100g=None, fiber_100g=None, origin="", category=""
        )
        self.assertEqual(self.summary(empty), [
            ("nutrition", True, ["fiber_100g", "sodium_100g"]),
            ("origin", True, ["origin"]),
            ("category", True, ["category"]),
        ])

    def test_category_and_name_need_a_tag(self):
        self.assertEqual(missing_data(make_complete_product(category="", product_name="")), [])

    def test_values_dict_and_broken_tags(self):
        row = {**COMPLETE_FIELDS, "misc_tags": None}
        self.assertEqual(missing_data(row), [])
        row["misc_tags"] = {"en:packagings-not-complete": True}
        self.assertEqual(missing_data(row), [])
        row["misc_tags"] = ["en:packagings-not-complete", 42]
        self.assertEqual([entry["key"] for entry in missing_data(row)], ["packaging"])

    def test_missing_count(self):
        self.assertEqual(missing_count([]), 0)
        self.assertEqual(missing_count([{"fields": ["fat_100g", "fiber_100g"]}, {"fields": []}]), 3)

    def test_incomplete_products_lists_active_products_by_missing_count(self):
        complete = make_complete_product()
        one = make_complete_product(fiber_100g=None, product_name="Satu")
        three = make_complete_product(
            fiber_100g=None, nova_group=None, misc_tags=["en:packagings-not-complete"], product_name="Tiga"
        )
        inactive = make_complete_product(fiber_100g=None, is_active=False)
        with self.assertNumQueries(1):
            rows = incomplete_products()
        self.assertEqual([row["pk"] for row in rows], [three.pk, one.pk])
        self.assertNotIn(complete.pk, [row["pk"] for row in rows])
        self.assertEqual(rows[0]["missing_count"], 3)
        self.assertEqual(rows[1], {
            "pk": one.pk, "product_name": "Satu", "brand": "Sarimi", "quantity": "88 g",
            "missing": [{"key": "nutrition", "label": "Gizi", "correctable": True, "fields": ["fiber_100g"]}],
            "missing_count": 1,
        })
        own_queryset = Product.objects.filter(pk__in=[inactive.pk, one.pk])
        self.assertEqual([row["pk"] for row in incomplete_products(own_queryset)], [one.pk])


class ResponseHelperTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def request(self, user=None, path="/moderasi/", **headers):
        request = self.factory.get(path, **headers)
        request.user = user or AnonymousUser()
        return request

    def test_wants_json(self):
        self.assertTrue(wants_json(self.request(path="/antrean/?format=json")))
        self.assertTrue(wants_json(self.request(HTTP_ACCEPT="application/json")))
        self.assertTrue(wants_json(self.request(HTTP_ACCEPT="text/html, application/json;q=0.9")))
        self.assertFalse(wants_json(self.request(HTTP_ACCEPT="text/html,application/xhtml+xml")))
        self.assertFalse(wants_json(self.request(path="/antrean/?format=html")))
        self.assertFalse(wants_json(self.request()))

    def test_json_ok_and_json_error_shapes(self):
        response = json_ok({"id": 3}, status=201)
        self.assertEqual((response.status_code, json.loads(response.content)), (201, {"id": 3}))
        errors = {"nova_group": [NOVA_MESSAGE], "brand": "Isian ini wajib diisi."}
        response = json_error("Periksa kembali isian koreksi.", errors)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {
            "error": {"id": "validation_error", "message": "Periksa kembali isian koreksi."},
            "fields": {
                "nova_group": [{"message": NOVA_MESSAGE, "code": "invalid"}],
                "brand": [{"message": "Isian ini wajib diisi.", "code": "invalid"}],
            },
        })
        response = json_error("Item ini sudah ditinjau.", status=409, error_id="already_reviewed")
        self.assertEqual(json.loads(response.content),
                         {"error": {"id": "already_reviewed", "message": "Item ini sudah ditinjau."}})

    def test_field_errors_accepts_form_errors(self):
        class BrandForm(forms.Form):
            brand = forms.CharField()

        form = BrandForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(field_errors(form.errors), form.errors.get_json_data())
        self.assertEqual(field_errors(form.errors)["brand"][0]["code"], "required")
        self.assertEqual(field_errors({"brand": [{"message": "x", "code": "y"}]}),
                         {"brand": [{"message": "x", "code": "y"}]})

    def test_page_payload(self):
        page = Paginator(list(range(30)), 12).page(2)
        self.assertEqual(page_payload(page, ({"n": n} for n in page)), {
            "count": 30, "page": 2, "page_size": 12, "results": [{"n": n} for n in range(12, 24)],
        })

    def test_render_or_json(self):
        build = mock.Mock(return_value={"id": 1})
        response = render_or_json(self.request(path="/x/?format=json"), "tidak/dipakai.html", {}, build)
        self.assertEqual(json.loads(response.content), {"id": 1})
        with mock.patch("data_correction.responses.render", return_value=HttpResponse("html")) as render:
            response = render_or_json(self.request(path="/x/"), "data_correction/queue.html", {"a": 1}, build)
        self.assertEqual(response.content, b"html")
        self.assertEqual(render.call_args.args[1:3], ("data_correction/queue.html", {"a": 1}))
        build.assert_called_once()  # data JSON tidak disusun untuk permintaan HTML
        response = render_or_json(self.request(path="/x/?format=json"), "x.html", {}, {"id": 2}, status=201)
        self.assertEqual((response.status_code, json.loads(response.content)), (201, {"id": 2}))

    def test_login_required_json(self):
        view = login_required_json(lambda request: HttpResponse("ok"))
        response = view(self.request(path="/antrean/saya/"))
        self.assertEqual((response.status_code, response.url), (302, "/masuk/?next=/antrean/saya/"))
        response = view(self.request(path="/antrean/saya/?format=json"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["error"]["id"], "authentication_required")
        self.assertEqual(view(self.request(make_user())).content, b"ok")

    def test_staff_required(self):
        view = staff_required(lambda request: HttpResponse("ok"))
        self.assertEqual(view(self.request()).url, "/masuk/?next=/moderasi/")
        self.assertEqual(view(self.request(path="/moderasi/?format=json")).status_code, 401)
        with self.assertRaises(PermissionDenied):
            view(self.request(make_user()))
        response = view(self.request(make_user("sari@email.com", "Sari"), path="/moderasi/?format=json"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content)["error"]["id"], "forbidden")
        self.assertEqual(view(self.request(make_staff())).content, b"ok")

    def test_decorators_keep_view_name(self):
        def curator_queue(request):
            return HttpResponse("ok")

        self.assertEqual(staff_required(curator_queue).__name__, "curator_queue")
        self.assertEqual(login_required_json(curator_queue).__name__, "curator_queue")


SUBMITTED_MESSAGE = "Pengajuan koreksi terkirim dan menunggu tinjauan kurator."
WITHDRAWN_MESSAGE = "Pengajuan berhasil ditarik."
NOT_WITHDRAWABLE_MESSAGE = "Pengajuan ini sudah mulai ditinjau sehingga tidak bisa ditarik."
EMPTY_MESSAGE = "Pilih minimal satu field untuk dikoreksi."
FORBIDDEN_MESSAGE = "Field ini tidak boleh dikoreksi."
DUPLICATE_MESSAGE = "Field ini diajukan lebih dari sekali."


def json_of(response):
    return json.loads(response.content)


def messages_of(response):
    """Pesan django.contrib.messages yang ditambahkan selama permintaan itu."""
    return [str(message) for message in get_messages(response.wsgi_request)]


class ViewTestMixin:
    """Pemeriksaan yang berulang di tes view Tahap 4."""

    def assertRedirectsTo(self, response, url):
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def assertLoginRedirect(self, response, next_url):
        self.assertRedirectsTo(response, f"/masuk/?next={next_url}")

    def assertJsonError(self, response, status, error_id):
        self.assertEqual((response.status_code, json_of(response)["error"]["id"]), (status, error_id))


class CorrectionFormTests(SimpleTestCase):
    """Form tanpa database: Product cukup objek yang tidak disimpan."""

    def setUp(self):
        self.product = Product(
            product_name="Sarimi Isi 2 Goreng", brand="", nova_group=4, sodium_100g=0.3976, fiber_100g=None
        )

    def form(self, data=None, **kwargs):
        return CorrectionForm(data, product=self.product, **kwargs)

    def test_one_optional_text_field_per_correctable_field(self):
        form = self.form()
        self.assertEqual(list(form.fields), list(constants.CORRECTABLE_FIELDS))
        for name, field in form.fields.items():
            with self.subTest(field=name):
                self.assertIs(type(field), forms.CharField)  # bukan FloatField/IntegerField
                self.assertFalse(field.required)
                self.assertEqual(field.label, constants.FIELD_LABELS[name])
        groups = form.groups()
        titles = [group["title"] for group in groups]
        self.assertEqual(titles, ["Info produk", "Tingkat pemrosesan", "Gizi per 100 g"])
        names = [row["field"].name for group in groups for row in group["rows"]]
        self.assertEqual(names, list(constants.CORRECTABLE_FIELDS))

    def test_inputs_use_inputmode_instead_of_number_type(self):
        form = self.form()
        for name in constants.CORRECTABLE_FIELDS:
            with self.subTest(field=name):
                html = str(form[name])
                self.assertIn('type="text"', html)
                self.assertNotIn('type="number"', html)
        for name in constants.NUTRITION_FIELDS:
            self.assertIn('inputmode="decimal"', str(form[name]))
        self.assertIn('inputmode="numeric"', str(form["nova_group"]))
        self.assertNotIn("inputmode", str(form["brand"]))
        self.assertIn('maxlength="255"', str(form["brand"]))  # dari model Product
        self.assertIn('maxlength="100"', str(form["quantity"]))

    def test_help_texts_name_unit_and_forbid_thousand_separators(self):
        for name in constants.NUTRITION_FIELDS:
            self.assertIn("tanpa pemisah ribuan", help_text_for(name))
        self.assertIn("dalam mg per 100 g", help_text_for("sodium_100g"))
        self.assertIn("dalam kkal per 100 g", help_text_for("energy_kcal_100g"))
        self.assertIn("dalam g per 100 g", help_text_for("fat_100g"))
        self.assertIn("1 sampai 4", help_text_for("nova_group"))
        self.assertEqual(help_text_for("brand"), "Maksimal 255 karakter.")
        self.assertEqual(self.form().fields["fiber_100g"].help_text, help_text_for("fiber_100g"))

    def test_focus_from_query_marks_fields_and_ignores_unknown_names(self):
        form = self.form(focus=["code", "proteins_100g", "fiber_100g", "proteins_100g"])
        self.assertEqual(form.focus, ["proteins_100g", "fiber_100g"])
        self.assertIn("autofocus", str(form["proteins_100g"]))  # hanya field pertama
        self.assertNotIn("autofocus", str(form["fiber_100g"]))
        rows = {row["field"].name: row for group in form.groups() for row in group["rows"]}
        self.assertTrue(rows["fiber_100g"]["focus"])
        self.assertFalse(rows["brand"]["focus"])
        self.assertEqual(rows["sodium_100g"]["value"], 0.3976)  # nilai kolom; template yang mengubah ke mg
        self.assertNotIn("autofocus", str(self.form()["proteins_100g"]))

    def test_changes_reads_raw_post_and_skips_empty_boxes(self):
        data = QueryDict(
            "csrfmiddlewaretoken=x&brand=+Sarimi+&fat_100g=&sugars_100g=+++&code=123&nova_group=3"
        )
        expected = [("brand", " Sarimi "), ("code", "123"), ("nova_group", "3")]
        self.assertEqual(self.form(data).changes(), expected)
        self.assertEqual(self.form({"brand": "Sarimi", "fat_100g": ""}).changes(), [("brand", "Sarimi")])

    def test_changes_keeps_every_value_of_a_repeated_field(self):
        data = QueryDict("brand=A&brand=B&fat_100g=&fat_100g=7")
        expected = [("brand", "A"), ("brand", "B"), ("fat_100g", ""), ("fat_100g", "7")]
        self.assertEqual(self.form(data).changes(), expected)

    def test_changes_stops_on_null_character(self):
        form = self.form(QueryDict("brand=Sari%00mi"))
        error = error_of(form.changes)
        self.assertEqual((error.error_id, error.status), ("validation_error", 400))
        self.assertEqual(list(error.fields), ["brand"])
        form.add_correction_error(error)  # pesan yang sama tidak dipasang dua kali
        self.assertEqual(len(form.errors["brand"]), 1)

    def test_add_correction_error(self):
        form = self.form(QueryDict("nova_group=5&code=1"))
        form.add_correction_error(CorrectionError(
            "validation_error", "Periksa kembali isian koreksi.",
            fields={"nova_group": [NOVA_MESSAGE], "code": [FORBIDDEN_MESSAGE]},
        ))
        self.assertEqual(form.errors["nova_group"], [NOVA_MESSAGE])
        self.assertEqual(form.non_field_errors(), [f"code: {FORBIDDEN_MESSAGE}"])
        form = self.form(QueryDict(""))
        form.add_correction_error(CorrectionError("validation_error", EMPTY_MESSAGE))
        self.assertEqual(form.non_field_errors(), [EMPTY_MESSAGE])

    def test_json_fields_use_column_units(self):
        fields = {entry["field_name"]: entry for entry in self.form().json_fields()}
        self.assertEqual(list(fields), list(constants.CORRECTABLE_FIELDS))
        self.assertEqual(fields["sodium_100g"], {
            "field_name": "sodium_100g", "label": "Natrium (mg/100 g)", "type": "number",
            "current_value": 0.3976, "display_factor": 1000, "help_text": help_text_for("sodium_100g"),
        })
        brand, nova, fiber = fields["brand"], fields["nova_group"], fields["fiber_100g"]
        self.assertEqual((brand["type"], brand["current_value"]), ("text", None))  # "" = tidak diketahui
        self.assertEqual((nova["type"], nova["current_value"]), ("integer", 4))
        self.assertEqual((fiber["current_value"], fiber["display_factor"]), (None, 1))


class DisplayValueFilterTests(SimpleTestCase):
    def test_display_value(self):
        cases = [
            ("0.78", "sodium_100g", "780"),
            (0.3976, "sodium_100g", "397,6"),
            ("0", "fiber_100g", "0"),
            ("3", "nova_group", "3"),
            ("Sarimi", "brand", "Sarimi"),
            (None, "fat_100g", "Tidak diketahui"),
            ("", "brand", "Tidak diketahui"),
        ]
        for value, field_name, expected in cases:
            with self.subTest(value=value, field=field_name):
                self.assertEqual(display_value(value, field_name), expected)

    def test_filter_is_registered(self):
        template = Template("{% load data_correction_tags %}{{ value|display_value:field }}")
        self.assertEqual(template.render(Context({"value": "0.78", "field": "sodium_100g"})), "780")


class SubmitViewTests(ViewTestMixin, TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(brand="Sarimi", nova_group=4, sodium_100g=0.3976)  # protein NULL
        self.url = reverse("data_correction:submit", args=[self.product.pk])

    def test_url_is_stable(self):
        self.assertEqual(self.url, f"/antrean/produk/{self.product.pk}/ajukan/")

    def test_visitor_is_sent_to_login_or_gets_401(self):
        self.assertLoginRedirect(self.client.get(self.url), self.url)
        self.assertLoginRedirect(self.client.post(self.url, {"brand": "Sarimi Baru"}), self.url)
        response = self.client.post(self.url + "?format=json", {"brand": "Sarimi Baru"})
        self.assertJsonError(response, 401, "authentication_required")
        self.assertFalse(DataCorrection.objects.exists())

    def test_get_shows_form_with_current_values(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url + "?field=proteins_100g")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "data_correction/submit.html")
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, "397,6")  # natrium 0.3976 g tampil dalam mg
        self.assertContains(response, "Tidak diketahui")  # protein NULL
        self.assertContains(response, 'inputmode="decimal"')
        self.assertNotContains(response, 'type="number"')
        self.assertContains(response, reverse("product_catalog:product_detail", args=[self.product.pk]))
        self.assertEqual(response.context["form"].focus, ["proteins_100g"])
        self.assertIn("autofocus", str(response.context["form"]["proteins_100g"]))

    def test_get_json_lists_correctable_fields(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        data = json_of(response)
        self.assertEqual(data["product"], {"id": self.product.pk, "product_name": self.product.product_name})
        fields = {entry["field_name"]: entry for entry in data["correctable_fields"]}
        self.assertEqual(list(fields), list(constants.CORRECTABLE_FIELDS))
        self.assertEqual(fields["sodium_100g"]["current_value"], 0.3976)
        self.assertIsNone(fields["proteins_100g"]["current_value"])

    def test_post_creates_correction_and_redirects_to_success_page(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"proteins_100g": "8,5", "sodium_100g": "780", "brand": ""})
        correction = DataCorrection.objects.get()
        detail = reverse("data_correction:correction_detail", args=[correction.pk])
        self.assertRedirectsTo(response, f"{detail}?terkirim=1")
        self.assertEqual(messages_of(response), [SUBMITTED_MESSAGE])
        self.assertEqual(correction.submitted_by, self.user)
        items = {item.field_name: item for item in correction.items.all()}
        self.assertEqual(set(items), {"proteins_100g", "sodium_100g"})
        protein, sodium = items["proteins_100g"], items["sodium_100g"]
        self.assertEqual((protein.old_value, protein.proposed_value), (None, "8.5"))
        self.assertEqual((sodium.old_value, sodium.proposed_value), ("0.3976", "0.78"))  # mg -> g
        self.product.refresh_from_db()
        self.assertIsNone(self.product.proteins_100g)  # Product baru berubah setelah disetujui kurator

    def test_success_page_after_redirect(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"sodium_100g": "780"}, follow=True)
        self.assertTemplateUsed(response, "data_correction/submit_success.html")
        self.assertContains(response, "Pengajuan berhasil dikirim")
        self.assertContains(response, SUBMITTED_MESSAGE)  # toast
        self.assertContains(response, "780")

    def test_post_json_returns_201(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url + "?format=json", {"sodium_100g": "780", "nova_group": "3"})
        self.assertEqual(response.status_code, 201)
        correction = DataCorrection.objects.get()
        data = json_of(response)
        created = correction.created_at
        expected_time = created.replace(microsecond=created.microsecond // 1000 * 1000)  # JSON: milidetik
        self.assertEqual(parse_datetime(data.pop("created_at")), expected_time)
        pending = {"status": PENDING, "status_label": "Menunggu", "review_note": ""}
        self.assertEqual(data, {
            "id": correction.pk,
            "product": {"id": self.product.pk, "product_name": self.product.product_name},
            "status": PENDING,
            "status_label": "Menunggu",
            "is_withdrawable": True,
            "items": [
                {"field_name": "nova_group", "label": "Grup NOVA", "old_value": 4, "proposed_value": 3,
                 **pending},
                {"field_name": "sodium_100g", "label": "Natrium (mg/100 g)", "old_value": 0.3976,
                 "proposed_value": 0.78, **pending},
            ],
        })

    def test_invalid_values_show_errors_and_keep_input(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"nova_group": "5", "fat_100g": "1.234,5"})
        self.assertEqual(response.status_code, 400)
        form = response.context["form"]
        self.assertEqual(form.errors["nova_group"], [NOVA_MESSAGE])
        self.assertEqual(form.errors["fat_100g"], [SEPARATOR_MESSAGE])
        self.assertContains(response, "Periksa kembali isian koreksi.", status_code=400)
        self.assertContains(response, 'value="1.234,5"', status_code=400)  # isian tidak hilang
        self.assertContains(response, 'aria-invalid="true"', status_code=400)
        response = self.client.post(self.url + "?format=json", {"nova_group": "5"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json_of(response), {
            "error": {"id": "validation_error", "message": "Periksa kembali isian koreksi."},
            "fields": {"nova_group": [{"message": NOVA_MESSAGE, "code": "invalid"}]},
        })
        self.assertFalse(DataCorrection.objects.exists())

    def test_empty_submission_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"brand": "  ", "fat_100g": ""})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context["form"].non_field_errors(), [EMPTY_MESSAGE])
        response = self.client.post(self.url + "?format=json", {})
        self.assertJsonError(response, 400, "validation_error")
        self.assertEqual(json_of(response)["error"]["message"], EMPTY_MESSAGE)
        self.assertFalse(DataCorrection.objects.exists())

    def test_forbidden_field_from_manual_post_is_rejected(self):
        self.client.force_login(self.user)
        code = self.product.code
        response = self.client.post(self.url, {"code": "1234567890123", "brand": "Sarimi Baru"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context["form"].non_field_errors(), [f"code: {FORBIDDEN_MESSAGE}"])
        response = self.client.post(self.url + "?format=json", {"is_active": "false"})
        self.assertJsonError(response, 400, "validation_error")
        expected = {"is_active": [{"message": FORBIDDEN_MESSAGE, "code": "invalid"}]}
        self.assertEqual(json_of(response)["fields"], expected)
        self.assertFalse(DataCorrection.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual((self.product.code, self.product.brand), (code, "Sarimi"))
        self.assertTrue(self.product.is_active)

    def test_duplicate_field_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"fat_100g": ["7", "8"]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context["form"].errors["fat_100g"], [DUPLICATE_MESSAGE])
        response = self.client.post(self.url + "?format=json", {"fat_100g": ["7", ""]})
        self.assertJsonError(response, 400, "validation_error")
        self.assertEqual(json_of(response)["fields"]["fat_100g"][0]["message"], DUPLICATE_MESSAGE)
        self.assertFalse(DataCorrection.objects.exists())

    def test_unchanged_value_and_null_character_are_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"brand": "Sarimi"})
        self.assertEqual(response.context["form"].errors["brand"], ["Usulan sama dengan nilai saat ini."])
        response = self.client.post(self.url, {"brand": "Sari\x00mi"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.context["form"].errors["brand"]), 1)
        response = self.client.post(self.url + "?format=json", {"brand": "Sari\x00mi"})
        self.assertJsonError(response, 400, "validation_error")
        self.assertEqual(list(json_of(response)["fields"]), ["brand"])
        self.assertFalse(DataCorrection.objects.exists())

    def test_inactive_or_missing_product_is_404(self):
        self.client.force_login(self.user)
        inactive = make_product(is_active=False)
        for pk in (inactive.pk, 999999):
            url = reverse("data_correction:submit", args=[pk])
            with self.subTest(pk=pk):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, {"brand": "Baru"}).status_code, 404)
                response = self.client.post(url + "?format=json", {"brand": "Baru"})
                self.assertJsonError(response, 404, "product_not_found")
        self.assertFalse(DataCorrection.objects.exists())

    def test_only_get_and_post_are_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.put(self.url).status_code, 405)
        self.assertEqual(self.client.delete(self.url).status_code, 405)


class MyCorrectionsViewTests(ViewTestMixin, TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("sari@email.com", "Sari")
        self.product = make_product(product_name="Sarimi Isi 2 Goreng")
        self.url = reverse("data_correction:my_corrections")

    def test_visitor_is_sent_to_login_or_gets_401(self):
        self.assertLoginRedirect(self.client.get(self.url), "/antrean/saya/")
        response = self.client.get(self.url, HTTP_ACCEPT="application/json")
        self.assertJsonError(response, 401, "authentication_required")

    def test_lists_only_own_corrections_newest_first(self):
        older = make_correction(self.product, self.user, brand=PENDING)
        newer = make_correction(self.product, self.user, fat_100g=APPROVED)
        theirs = make_correction(make_product(product_name="Produk Milik Sari"), self.other, brand=PENDING)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "data_correction/my_corrections.html")
        self.assertEqual(list(response.context["page_obj"]), [newer, older])
        self.assertNotContains(response, "Produk Milik Sari")
        self.assertNotContains(response, reverse("data_correction:correction_detail", args=[theirs.pk]))
        data = json_of(self.client.get(self.url + "?format=json"))
        self.assertEqual((data["count"], data["page"], data["page_size"]), (2, 1, 10))
        self.assertEqual([row["id"] for row in data["results"]], [newer.pk, older.pk])

    def test_shows_derived_status_item_status_and_curator_note(self):
        correction = make_correction(self.product, self.user, fat_100g=APPROVED, fiber_100g=REJECTED)
        correction.items.filter(field_name="fiber_100g").update(
            proposed_value="2.5", review_note="Tidak sesuai label."
        )
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        texts = ("Sebagian disetujui", "Disetujui", "Ditolak", "Catatan kurator: Tidak sesuai label.", "2,5")
        for text in texts:
            self.assertContains(response, text)
        self.assertNotContains(response, reverse("data_correction:withdraw", args=[correction.pk]))
        row = json_of(self.client.get(self.url + "?format=json"))["results"][0]
        summary = (row["status"], row["status_label"], row["is_withdrawable"])
        self.assertEqual(summary, (PARTIAL, "Sebagian disetujui", False))
        self.assertEqual(row["items"][1], {
            "field_name": "fiber_100g", "label": "Serat (g/100 g)", "old_value": None, "proposed_value": 2.5,
            "status": REJECTED, "status_label": "Ditolak", "review_note": "Tidak sesuai label.",
        })

    def test_withdraw_button_only_for_unreviewed_corrections(self):
        pending = make_correction(self.product, self.user, brand=PENDING, fat_100g=PENDING)
        reviewed = make_correction(self.product, self.user, brand=PENDING, fat_100g=REJECTED)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, reverse("data_correction:withdraw", args=[pending.pk]))
        self.assertNotContains(response, reverse("data_correction:withdraw", args=[reviewed.pk]))

    def test_empty_state_and_pagination(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(self.url), "Belum ada pengajuan.")
        for _ in range(12):
            make_correction(self.product, self.user, brand=PENDING)
        data = json_of(self.client.get(self.url + "?format=json&page=2"))
        self.assertEqual((data["count"], data["page"], len(data["results"])), (12, 2, 2))
        self.assertContains(self.client.get(self.url + "?page=2"), "Halaman 2 dari 2")

    def test_query_count_does_not_grow_with_corrections(self):
        self.client.force_login(self.user)
        make_correction(self.product, self.user, brand=PENDING)
        with CaptureQueriesContext(connection) as few:
            self.client.get(self.url)
        for _ in range(5):
            make_correction(make_product(), self.user, brand=PENDING, fat_100g=APPROVED)
        with CaptureQueriesContext(connection) as many:
            self.client.get(self.url)
        self.assertEqual(len(many), len(few))
        with CaptureQueriesContext(connection) as many_json:
            self.client.get(self.url + "?format=json")
        self.assertEqual(len(many_json), len(few))


class CorrectionDetailViewTests(ViewTestMixin, TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("sari@email.com", "Sari")
        self.product = make_product()
        self.correction = make_correction(self.product, self.user, sodium_100g=PENDING)  # usulan "1" g
        self.url = reverse("data_correction:correction_detail", args=[self.correction.pk])

    def test_url_and_visitor(self):
        self.assertEqual(self.url, f"/antrean/saya/{self.correction.pk}/")
        self.assertLoginRedirect(self.client.get(self.url), self.url)
        self.assertJsonError(self.client.get(self.url + "?format=json"), 401, "authentication_required")

    def test_own_detail_html_and_json(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "Detail pengajuan")
        self.assertNotContains(response, "Pengajuan berhasil dikirim")
        self.assertContains(response, "1000")  # 1 g natrium tampil 1000 mg
        self.assertContains(response, reverse("data_correction:withdraw", args=[self.correction.pk]))
        self.assertContains(response, reverse("product_catalog:product_detail", args=[self.product.pk]))
        self.assertContains(self.client.get(self.url + "?terkirim=1"), "Pengajuan berhasil dikirim")
        data = json_of(self.client.get(self.url + "?format=json"))
        self.assertEqual((data["id"], data["status"]), (self.correction.pk, PENDING))
        self.assertEqual(data["items"][0]["proposed_value"], 1.0)

    def test_someone_elses_correction_is_404(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertJsonError(self.client.get(self.url + "?format=json"), 404, "correction_not_found")

    def test_no_product_link_or_withdraw_for_inactive_product_and_reviewed_item(self):
        Product.objects.filter(pk=self.product.pk).update(is_active=False)
        self.correction.items.update(status=APPROVED)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, reverse("product_catalog:product_detail", args=[self.product.pk]))
        self.assertNotContains(response, reverse("data_correction:withdraw", args=[self.correction.pk]))
        self.assertContains(response, "Disetujui")


class WithdrawViewTests(ViewTestMixin, TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("sari@email.com", "Sari")
        self.correction = make_correction(make_product(), self.user, brand=PENDING, fat_100g=PENDING)
        self.url = reverse("data_correction:withdraw", args=[self.correction.pk])
        self.list_url = reverse("data_correction:my_corrections")

    def assertStillExists(self):
        self.assertTrue(DataCorrection.objects.filter(pk=self.correction.pk).exists())
        self.assertEqual(DataCorrectionItem.objects.filter(correction_id=self.correction.pk).count(), 2)

    def test_url_visitor_and_get(self):
        self.assertEqual(self.url, f"/antrean/saya/{self.correction.pk}/tarik/")
        self.assertLoginRedirect(self.client.post(self.url), self.url)
        self.assertJsonError(self.client.post(self.url + "?format=json"), 401, "authentication_required")
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)  # wajib POST
        self.assertStillExists()

    def test_withdraw_own_pending_correction(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirectsTo(response, self.list_url)
        self.assertEqual(messages_of(response), [WITHDRAWN_MESSAGE])
        self.assertFalse(DataCorrection.objects.exists())
        self.assertFalse(DataCorrectionItem.objects.exists())

    def test_withdraw_json(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url + "?format=json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json_of(response), {"deleted": True, "id": self.correction.pk})
        response = self.client.post(self.url + "?format=json")  # sudah tidak ada
        self.assertJsonError(response, 404, "correction_not_found")

    def test_cannot_withdraw_someone_elses_correction(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url).status_code, 404)
        response = self.client.post(self.url, HTTP_ACCEPT="application/json")
        self.assertJsonError(response, 404, "correction_not_found")
        self.assertStillExists()

    def test_cannot_withdraw_after_any_review(self):
        reviewed = self.correction.items.filter(field_name="fat_100g")
        reviewed.update(status=REJECTED, review_note="Tidak sesuai.")
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirectsTo(response, self.list_url)
        self.assertEqual(messages_of(response), [NOT_WITHDRAWABLE_MESSAGE])
        response = self.client.post(self.url + "?format=json")
        self.assertJsonError(response, 409, "not_withdrawable")
        self.assertEqual(json_of(response)["error"]["message"], NOT_WITHDRAWABLE_MESSAGE)
        self.assertStillExists()