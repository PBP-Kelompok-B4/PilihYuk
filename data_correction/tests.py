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

from product_catalog.models import Product

from . import constants
from .checks import check_correctable_fields
from .constants import APPROVED, CORRECTION_STATUS_LABELS, PARTIAL, PENDING, REJECTED
from .models import DataCorrection, DataCorrectionItem

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