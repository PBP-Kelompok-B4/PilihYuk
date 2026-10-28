"""Aturan Modul 4 (Antrean Data): ajukan, tarik, setujui, tolak.

Notes:
- Semua aturan yang MENGUBAH data koreksi dikumpulkan di sini, tanpa
  urusan tampilan. View HTML, endpoint JSON (untuk Flutter), dan tes cukup memanggil
  fungsi-fungsi di file ini, jadi aturannya hanya ditulis sekali.
- Daftar fungsi publik:
  - submit_correction   : pengguna mengajukan koreksi (PRD F-4.1 sampai F-4.3)
  - withdraw_correction : pengguna menarik pengajuannya (F-4.5)
  - approve_item        : kurator menyetujui satu field, nilainya ditulis ke Product (F-4.4)
  - reject_item         : kurator menolak satu field dengan catatan wajib (F-4.4)
- Keamanan data:
  - Semua perubahan berjalan di dalam transaction.atomic: kalau satu langkah gagal,
    semua langkah dibatalkan, jadi tidak ada data setengah jadi.
  - Baris yang akan diubah dikunci dengan select_for_update, supaya dua orang tidak
    bisa mengubah baris yang sama pada saat bersamaan (mis. pengaju menarik pengajuan
    tepat ketika kurator menyetujuinya).
  - Urutan kunci SELALU pengajuan -> item -> produk. Urutan yang tetap mencegah dua
    proses saling menunggu selamanya (deadlock) di PostgreSQL.
  - SQLite mengabaikan select_for_update, jadi kode yang sama tetap berjalan di lokal
    (SQLite) maupun di PWS (PostgreSQL).
- Cara melaporkan error: fungsi melempar CorrectionError, yang membawa:
  - error_id dan status untuk JSON, mis. "already_reviewed" dan 409;
  - message untuk toast atau pesan di atas form;
  - fields berisi pesan per field, mis. {"brand": ["Isian ini wajib diisi."]}.
    View bisa memasukkannya ke form (form.add_error) atau ke JSON (responses.json_error).
"""
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from product_catalog.models import Product

from .constants import APPROVED, CORRECTABLE_FIELDS, PENDING, REJECTED
from .models import DataCorrection, DataCorrectionItem
from .validators import get_current_value, parse_proposed_value, to_stored_text


class CorrectionError(Exception):
    """Permintaan ditolak dengan alasan yang boleh ditampilkan ke pengguna.

    Atribut:
        error_id : kode singkat untuk JSON, mis. "not_withdrawable"
        message  : kalimat untuk pengguna
        status   : kode HTTP yang sesuai (400, 401, 403, 404, atau 409)
        fields   : pesan error per field, kosong kalau bukan error validasi

    Contoh:
        CorrectionError("not_withdrawable", "Pengajuan ini sudah mulai ditinjau ...", 409)
        CorrectionError("validation_error", "Periksa kembali isian koreksi.", 400,
                        fields={"nova_group": ["Grup NOVA harus bilangan bulat 1 sampai 4."]})
    """

    def __init__(self, error_id, message, status=400, fields=None):
        super().__init__(message)
        self.error_id = error_id
        self.message = message
        self.status = status
        self.fields = fields or {}


@dataclass(frozen=True)
class ReviewResult:
    """Hasil tinjauan satu item (dikembalikan approve_item dan reject_item).

    Atribut:
        item  : item yang sudah ditinjau (status sudah approved/rejected)
        stale : True kalau nilai Product sudah berubah sejak diajukan (berbeda dari
                old_value). Persetujuan tetap dijalankan, tetapi UI bisa memberi
                peringatan ke kurator.

    Contoh:
        ReviewResult(item=<item approved>, stale=False)
    """

    item: DataCorrectionItem
    stale: bool = False


def submit_correction(user, product, changes):
    """Buat satu DataCorrection berisi satu item per field yang diubah.

    Argumen:
        user    : pengguna yang mengajukan (wajib sudah login)
        product : produk yang dikoreksi (wajib aktif)
        changes : {field_name: isian}, atau daftar pasangan [(field_name, isian), ...].
                  Bentuk daftar dipakai kalau sumbernya bisa memuat field yang sama dua
                  kali (mis. array JSON), karena dict tidak bisa berisi kunci ganda.
    Natrium diisi dalam mg; nilai yang disimpan sudah gram (lihat validators.py).

    Contoh:
        submit_correction(budi, sarimi, {"brand": "Sarimi", "sodium_100g": "780"})
            -> <DataCorrection> berisi item brand (old_value None, proposed_value "Sarimi")
               dan item sodium_100g (old_value "0.3976", proposed_value "0.78")
        submit_correction(budi, sarimi, {})
            -> CorrectionError("validation_error", "Pilih minimal satu field untuk dikoreksi.")
        submit_correction(budi, sarimi, {"code": "1", "nova_group": "5"})
            -> CorrectionError(..., fields={"code": ["Field ini tidak boleh dikoreksi."],
                                            "nova_group": ["Grup NOVA harus bilangan bulat 1 sampai 4."]})
    """

    if not getattr(user, "is_authenticated", False):
        raise CorrectionError("authentication_required", "Silakan masuk terlebih dahulu.", 401)

    pairs = list(changes.items()) if isinstance(changes, Mapping) else list(changes or ())
    pairs = [(str(name), raw) for name, raw in pairs]
    if not pairs:
        raise CorrectionError("validation_error", "Pilih minimal satu field untuk dikoreksi.")
    # Hitung kemunculan tiap field untuk mendeteksi field ganda (PRD F-4.3).
    counts = Counter(name for name, _ in pairs)

    with transaction.atomic():
        locked = Product.objects.select_for_update().filter(pk=product.pk).first()
        if locked is None:
            raise CorrectionError("product_not_found", "Produk tidak ditemukan.", 404)
        if not locked.is_active:
            raise CorrectionError(
                "product_inactive", "Produk ini tidak aktif sehingga tidak bisa dikoreksi.", 409
            )

        errors, values = {}, {}
        for name, raw in pairs:
            if counts[name] > 1:
                errors[name] = ["Field ini diajukan lebih dari sekali."]
                continue
            value, error = parse_proposed_value(name, raw, product=locked)
            if error:
                errors[name] = [error]
            else:
                values[name] = value
        if errors:
            raise CorrectionError("validation_error", "Periksa kembali isian koreksi.", fields=errors)

        correction = DataCorrection.objects.create(product=locked, submitted_by=user)
        DataCorrectionItem.objects.bulk_create([
            DataCorrectionItem(
                correction=correction,
                field_name=name,
                old_value=get_current_value(locked, name),          # nilai saat diajukan (F-4.3)
                proposed_value=to_stored_text(name, values[name]),  # satuan kolom
            )
            for name in CORRECTABLE_FIELDS  # urutan tetap, apa pun urutan isian
            if name in values
        ])
    return correction


def withdraw_correction(user, correction):
    """Hapus pengajuan milik user selama SEMUA item-nya masih pending.

    Hasil: pk pengajuan yang dihapus.
    Pengajuan milik orang lain dijawab "tidak ditemukan" (404), bukan "dilarang" (403),
    agar keberadaan pengajuan orang lain tidak terbuka.

    Contoh:
        withdraw_correction(budi, <milik budi, semua pending>)  -> 12
        withdraw_correction(budi, <ada item disetujui>)         -> CorrectionError("not_withdrawable", ..., 409)
        withdraw_correction(sari, <milik budi>)                 -> CorrectionError("correction_not_found", ..., 404)
    """
    with transaction.atomic():
        # Kunci pengajuan, sekaligus pastikan pemiliknya adalah user ini.
        locked = (
            DataCorrection.objects.select_for_update()
            .filter(pk=correction.pk, submitted_by_id=getattr(user, "pk", None))
            .first()
        )
        if locked is None or not getattr(user, "is_authenticated", False):
            raise CorrectionError("correction_not_found", "Pengajuan tidak ditemukan.", 404)
        # Kunci item-item-nya, lalu pastikan belum ada yang ditinjau kurator.
        statuses = list(locked.items.select_for_update().values_list("status", flat=True))
        if any(status != PENDING for status in statuses):
            raise CorrectionError(
                "not_withdrawable", "Pengajuan ini sudah mulai ditinjau sehingga tidak bisa ditarik.", 409
            )
        deleted_pk = locked.pk
        locked.delete()
    return deleted_pk


def approve_item(reviewer, item, note=""):
    """Setujui satu item: tulis nilainya ke Product, lalu tandai item approved.

    Nilai dikonversi ulang dengan parse_proposed_value (dari teks simpanan, satuan kolom),
    jadi aturan validasinya sama dengan saat diajukan. Catatan kurator opsional.

    Contoh:
        approve_item(kurator, <item nova_group "3">)        -> ReviewResult(item=<approved>, stale=False);
                                                               product.nova_group menjadi 3 (int)
        approve_item(kurator, <nilai produk sudah diubah>)  -> ReviewResult(..., stale=True)
        approve_item(budi, item)                            -> CorrectionError("forbidden", ..., 403)
        approve_item(kurator, <item sudah ditinjau>)        -> CorrectionError("already_reviewed", ..., 409)
    """
    _ensure_staff(reviewer)
    note = (note or "").strip()
    with transaction.atomic():
        # Kunci pengajuan -> item -> produk (urutan tetap, lihat CATATAN di atas file).
        correction, locked = _lock_pending_item(item)
        product = Product.objects.select_for_update().get(pk=correction.product_id)
        if not product.is_active:
            raise CorrectionError("product_inactive", "Produk ini tidak aktif; tolak item ini.", 409)

        # display_units=False: proposed_value sudah dalam satuan kolom (natrium gram),
        # jadi tidak boleh dibagi 1000 lagi.
        value, error = parse_proposed_value(locked.field_name, locked.proposed_value, display_units=False)
        if error:
            # Mis. max_length kolom Product diperkecil setelah pengajuan dibuat.
            raise CorrectionError(
                "validation_error", "Nilai usulan tidak lagi valid; tolak item ini.",
                fields={locked.field_name: [error]},
            )

        # Bandingkan nilai Product sekarang dengan nilai saat diajukan.
        stale = get_current_value(product, locked.field_name) != locked.old_value
        setattr(product, locked.field_name, value)
        product.save(update_fields=[locked.field_name, "updated_at"])
        _finish_review(reviewer, correction, locked, APPROVED, note)
    return ReviewResult(item=locked, stale=stale)


def reject_item(reviewer, item, note=""):
    """Tolak satu item dengan catatan wajib. Product sama sekali tidak disentuh.

    Contoh:
        reject_item(kurator, item, "Sumber tidak sesuai label")  -> ReviewResult(item=<rejected>)
        reject_item(kurator, item, "   ")                         -> CorrectionError("validation_error", ...,
                                                                      fields={"review_note": [...]})
    """
    _ensure_staff(reviewer)
    note = (note or "").strip()
    # Catatan wajib saat menolak, supaya pengaju tahu alasannya (keputusan 4).
    if not note:
        raise CorrectionError(
            "validation_error", "Catatan wajib diisi saat menolak.",
            fields={"review_note": ["Tulis alasan penolakan untuk pengaju."]},
        )
    with transaction.atomic():
        correction, locked = _lock_pending_item(item)
        _finish_review(reviewer, correction, locked, REJECTED, note)
    return ReviewResult(item=locked)


def _ensure_staff(user):
    """Hanya kurator (is_staff) yang boleh meninjau.

    Contoh:
        <kurator>                            -> None (lolos)
        <pengguna biasa> atau AnonymousUser  -> CorrectionError("forbidden", ..., 403)
    """
    if not getattr(user, "is_staff", False):
        raise CorrectionError("forbidden", "Hanya kurator yang bisa meninjau koreksi.", 403)


def _lock_pending_item(item):
    """Kunci pengajuan lalu item (urutan tetap), dan pastikan item masih pending.
    Data diambil ulang dari database, bukan dari objek `item` yang dikirim pemanggil,
    karena objek itu bisa saja sudah basi (mis. sudah ditinjau kurator lain).

    Contoh:
        <item pending>                        -> (<DataCorrection terkunci>, <item terkunci>)
        <item yang pengajuannya sudah ditarik> -> CorrectionError("correction_not_found", ..., 404)
        <item yang sudah ditinjau>            -> CorrectionError("already_reviewed", ..., 409)
    """
    correction = DataCorrection.objects.select_for_update().filter(pk=item.correction_id).first()
    locked = None
    if correction is not None:
        locked = (
            DataCorrectionItem.objects.select_for_update()
            .filter(pk=item.pk, correction=correction)
            .first()
        )
    if locked is None:
        raise CorrectionError("correction_not_found", "Pengajuan tidak ditemukan atau sudah ditarik.", 404)
    if locked.status != PENDING:
        raise CorrectionError("already_reviewed", "Item ini sudah ditinjau.", 409)
    # Pasang objek pengajuan yang sudah terkunci, agar tidak ada query tambahan.
    locked.correction = correction
    return correction, locked


def _finish_review(reviewer, correction, item, status, note):
    """Simpan hasil tinjauan item dan catat peninjau terakhir pada pengajuan.
    reviewed_by dan reviewed_at diisi SETIAP kali satu item ditinjau, jadi artinya
    "peninjau dan waktu tinjauan terakhir" (keputusan setelah Tahap 0).

    Contoh:
        (kurator, <pengajuan>, <item>, "approved", "")
            -> item.status = "approved"; correction.reviewed_by = kurator;
               correction.reviewed_at = waktu sekarang
    """
    item.status = status
    item.review_note = note
    item.save(update_fields=["status", "review_note"])
    correction.reviewed_by = reviewer
    correction.reviewed_at = timezone.now()
    correction.save(update_fields=["reviewed_by", "reviewed_at"])