"""Frekuensi produk di shelf publik untuk antrean kontribusi

Notes:
- Model app shelves diambil lewat apps.get_model di dalam fungsi, bukan diimpor di atas
  file. Kalau app itu tidak terpasang atau nama kolomnya berubah, hasilnya
  available=False dan antrean kembali ke urutan Tahap 6 tanpa error.
- Frekuensi = jumlah shelf PUBLIK berbeda yang memuat produk itu (keputusan Tahap 10).
  Shelf privat tidak dihitung karena isinya hanya boleh terlihat pemiliknya (F-2.2).
- Satu query agregat (values + annotate Count) untuk semua produk, bukan satu per produk.
- Kolom shelves yang dipakai: ShelfItem.product, ShelfItem.shelf, Shelf.is_private.
- Tabel yang belum dimigrasi (DatabaseError) sengaja tidak ditangkap: itu salah pasang,
  bukan keadaan yang perlu disembunyikan.
"""
from dataclasses import dataclass, field

from django.apps import apps
from django.core.exceptions import FieldError
from django.db.models import Count


@dataclass(frozen=True)
class ShelfFrequency:
    counts: dict = field(default_factory=dict)
    available: bool = False

    def of(self, product_pk):
        """Frekuensi satu produk; None kalau data shelf tidak tersedia."""
        return self.counts.get(product_pk, 0) if self.available else None


def shelf_counts(product_ids=None):
    try:
        shelf_item = apps.get_model("shelves", "ShelfItem")
        items = shelf_item.objects.filter(shelf__is_private=False)
        if product_ids is not None:
            items = items.filter(product_id__in=product_ids)
        rows = items.values("product_id").annotate(total=Count("shelf", distinct=True)).order_by()
        counts = {row["product_id"]: row["total"] for row in rows}
    except (LookupError, ImportError, FieldError):
        return ShelfFrequency()
    if product_ids is not None:
        counts = {pk: counts.get(pk, 0) for pk in product_ids}
    return ShelfFrequency(counts, available=True)