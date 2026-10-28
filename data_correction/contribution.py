"""Antrean kontribusi di /antrean/ (PRD F-4.7): produk aktif yang datanya belum lengkap.

Notes:
- Aturan "belum lengkap" TIDAK ditulis ulang di sini. Semuanya dari incomplete.py
  (incomplete_products dan CATEGORIES); file ini hanya menyaring, mengurutkan, menghitung
  status dan statistik, lalu menyusun tautan.
- Frekuensi shelf datang dari shelf_frequency.py. Kalau tidak tersedia, urutan shelf
  disembunyikan dan bawaannya kembali ke "Paling banyak data kosong"

Daftar isi:
1. ContributionFilters : membaca ?sort=, ?missing=, ?page= dan menyusun URL antrean.
2. queue_products, sort_rows : produk belum lengkap, sudah disaring dan diurutkan.
3. pending_product_ids, page_images, decorate : status, gambar, bar shelf, dan tautan per baris.
4. contribution_stats : kartu statistik.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from typing import NamedTuple
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone

from product_catalog.models import Product

from .constants import APPROVED, CORRECTABLE_FIELDS, PENDING
from .incomplete import CATEGORIES, incomplete_products
from .models import DataCorrection, DataCorrectionItem
from .shelf_frequency import shelf_counts

SORTS = (
    ("shelf", "Paling sering di shelf"),
    ("kosong", "Paling banyak data kosong"),
    ("terbaru", "Terbaru"),
)
SHELF_SORT = "shelf" 
FALLBACK_SORT = "kosong"  

CATEGORY_LABELS = {key: label for key, label, _ in CATEGORIES}  # "nutrition" -> "Gizi", dst.
OLDEST = datetime.min.replace(tzinfo=dt_timezone.utc)  # cadangan urutan terbaru (lihat sort_rows)

NEEDS_CONTRIBUTION = "needs_contribution"
NEEDS_VERIFICATION = "needs_verification"
STATUS_LABELS = {
    NEEDS_CONTRIBUTION: "Perlu kontribusi",
    NEEDS_VERIFICATION: "Perlu verifikasi",
}


@dataclass(frozen=True)
class ContributionFilters:
    """Keadaan halaman antrean kontribusi yang dibaca dari query string.
    Nilai yang tidak dikenal kembali ke bawaan diam-diam, sama seperti QueueFilters.

    Contoh:
        ContributionFilters.from_query({"sort": "terbaru", "missing": "nova"})
            -> ContributionFilters(sort="terbaru", missing="nova", page="", shelf_available=True)
        ContributionFilters.from_query({"sort": "acak", "missing": "code"})
            -> ContributionFilters(sort="shelf", missing="", ...)
        ContributionFilters.from_query({"sort": "shelf"}, shelf_available=False)
            -> ContributionFilters(sort="kosong", ..., shelf_available=False)
    """

    sort: str = SHELF_SORT
    missing: str = ""  # key kategori dari incomplete.CATEGORIES, kosong = semua
    page: str = ""
    shelf_available: bool = True  # dari shelf_frequency.shelf_counts().available

    @property
    def default_sort(self):
        return SHELF_SORT if self.shelf_available else FALLBACK_SORT

    @property
    def sorts(self):
        """Pilihan urutan; "shelf" hanya ada kalau data shelf tersedia."""
        return [(key, label) for key, label in SORTS if key != SHELF_SORT or self.shelf_available]

    @classmethod
    def from_query(cls, query, shelf_available=True):
        defaults = cls(shelf_available=shelf_available)
        sort = query.get("sort", "")
        missing = query.get("missing", "")
        return cls(
            sort=sort if sort in dict(defaults.sorts) else defaults.default_sort,
            missing=missing if missing in CATEGORY_LABELS else "",
            page=query.get("page", ""),
            shelf_available=shelf_available,
        )

    def url(self, **changes):
        """URL /antrean/ dengan filter sekarang; sebagian bisa diganti lewat argumen.
        Nilai kosong dan urutan bawaan tidak ditulis, jadi URL tetap pendek.

        Contoh (filter sekarang: sort "terbaru", missing "nutrition"):
            url()            -> "/antrean/?sort=terbaru&missing=nutrition"
            url(page=2)      -> "/antrean/?sort=terbaru&missing=nutrition&page=2"
            url(missing="")  -> "/antrean/?sort=terbaru"
        """
        values = {"sort": self.sort, "missing": self.missing, "page": self.page, **changes}
        if values["sort"] == self.default_sort:
            values["sort"] = ""
        query = urlencode({key: value for key, value in values.items() if value not in ("", None)})
        base = reverse("data_correction:contribution_queue")
        return f"{base}?{query}" if query else base

    def sort_chips(self):
        """Chip "Urutkan:". Mengganti urutan kembali ke halaman 1, filter tetap."""
        return [
            {"label": label, "url": self.url(sort=key, page=""), "active": key == self.sort}
            for key, label in self.sorts
        ]

    def missing_chips(self, categories):
        """Chip "Semua data" + satu chip per kategori yang benar-benar ada di antrean.

        Argumen:
            categories : key kategori yang muncul, urut seperti CATEGORIES (dari queue_products)
        """
        chips = [{"label": "Semua data", "url": self.url(missing="", page=""), "active": not self.missing}]
        chips += [
            {
                "label": CATEGORY_LABELS[key],
                "url": self.url(missing=key, page=""),
                "active": key == self.missing,
            }
            for key in categories
        ]
        return chips

    def page_links(self, page):
        """URL halaman sebelum dan sesudah (None kalau tidak ada) serta nomor halaman, dengan
        filter yang sama. Nomor halaman yang jauh diganti "…" (Paginator.get_elided_page_range).

        Contoh (halaman 9 dari 18):
            {"previous": "/antrean/?page=8", "next": "/antrean/?page=10",
             "pages": [{"number": 1, "url": "/antrean/?page=1", "current": False},
                       {"ellipsis": True}, ..., {"number": 18, ...}]}   -> 1, …, 8, 9, 10, …, 18
        """
        pages = []
        for number in page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1):
            if number == page.paginator.ELLIPSIS:
                pages.append({"ellipsis": True})
                continue
            pages.append({"number": number, "url": self.url(page=number), "current": number == page.number})
        return {
            "previous": self.url(page=page.previous_page_number()) if page.has_previous() else None,
            "next": self.url(page=page.next_page_number()) if page.has_next() else None,
            "pages": pages,
        }


class QueueResult(NamedTuple):
    """Hasil queue_products.

    - rows       : baris yang sudah disaring dan diurutkan, masing-masing dengan shelf_count
                   (None kalau data shelf tidak tersedia)
    - categories : key kategori yang muncul di antrean, urut seperti CATEGORIES (untuk chip)
    - total      : jumlah produk belum lengkap, tanpa filter
    - shelf_total: jumlah frekuensi shelf semua produk itu, tanpa filter (None kalau tidak
                   tersedia); dipakai kartu "Rata-rata di shelf"
    """

    rows: list
    categories: list
    total: int
    shelf_total: int | None


def queue_products(filters, frequency=None):
    """Semua produk belum lengkap, sudah disaring ?missing= dan diurutkan ?sort=.

    Argumen:
        frequency : hasil shelf_frequency.shelf_counts(); kalau None diambil di sini

    Contoh (data seed, misc_tags kosong, belum ada shelf):
        queue_products(ContributionFilters(missing="nova"))
            -> QueueResult(rows=[186 baris yang kurang NOVA],
                           categories=["nutrition", "nova", "brand", "quantity", "origin"],
                           total=347, shelf_total=0)
    """
    frequency = frequency if frequency is not None else shelf_counts()
    rows = [{**row, "shelf_count": frequency.of(row["pk"])} for row in incomplete_products()]
    present = {entry["key"] for row in rows for entry in row["missing"]}
    categories = [key for key, _, _ in CATEGORIES if key in present]
    shelf_total = sum(row["shelf_count"] for row in rows) if frequency.available else None
    total = len(rows)
    if filters.missing:
        rows = [row for row in rows if any(entry["key"] == filters.missing for entry in row["missing"])]
    return QueueResult(sort_rows(rows, filters.sort), categories, total, shelf_total)


def sort_rows(rows, sort):
    """Urutkan baris antrean. Pengurutan Python stabil (juga dengan reverse=True), jadi
    urutan nama A-Z lalu pk dipasang dulu sebagai pemecah seri, baru kunci utamanya.

    - shelf   : frekuensi shelf terbanyak, lalu data kurang terbanyak, lalu nama
    - terbaru : produk yang paling baru masuk katalog
    - kosong  : data kurang terbanyak, lalu nama

    Contoh:
        [Bihun (1 kurang), apel kering (1), Zebra (2)], "kosong"  -> [Zebra, apel kering, Bihun]
        [Bihun (1 kurang, 3 shelf), Zebra (2 kurang, 0 shelf)], "shelf"  -> [Bihun, Zebra]
    """
    rows = sorted(rows, key=lambda row: ((row["product_name"] or "").casefold(), row["pk"]))
    if sort == "terbaru":
        added = dict(Product.objects.values_list("pk", "created_at"))
        return sorted(rows, key=lambda row: added.get(row["pk"], OLDEST), reverse=True)
    if sort == SHELF_SORT:
        return sorted(rows, key=lambda row: (row.get("shelf_count") or 0, row["missing_count"]), reverse=True)
    return sorted(rows, key=lambda row: row["missing_count"], reverse=True)


def pending_product_ids(product_ids):
    """Id produk (dari daftar yang diberikan) yang sudah punya item koreksi pending.
    Satu query untuk seluruh halaman, bukan satu query per baris.

    Contoh: pending_product_ids([6, 7, 107]) -> {6}
    """
    return set(
        DataCorrectionItem.objects.filter(status=PENDING, correction__product_id__in=product_ids)
        .values_list("correction__product_id", flat=True)
    )

def page_images(product_ids):
    """URL gambar produk untuk satu halaman antrean (kotak gambar di tabel). Satu query.
    Produk tanpa gambar mendapat "" dan template menampilkan placeholder.

    Contoh: page_images([6, 7]) -> {6: "https://images.openfoodfacts.org/...jpg", 7: ""}
    """
    return dict(Product.objects.filter(pk__in=product_ids).values_list("pk", "image_url"))


def decorate(row, pending_ids, images=None, shelf_max=0):
    """Satu baris siap tampil: tambah status, status_label, submit_url, detail_url,
    image_url (dari page_images; kosong kalau tidak diberikan), dan shelf_bar.

    - status     : "needs_verification" kalau produk sudah punya item pending,
                   selain itu "needs_contribution".
    - submit_url : ?field= untuk SETIAP field kosong yang bisa dikoreksi, urut seperti form
                   (CORRECTABLE_FIELDS), jadi kotak kosong pertama mendapat autofocus.
                   Produk yang hanya punya kategori informasi mendapat URL tanpa ?field=.
                   Pengunjung yang membukanya diarahkan ke halaman masuk oleh view submit.
    - detail_url : halaman produk di katalog (product_catalog:product_detail).
    - shelf_bar  : lebar bar frekuensi shelf dalam persen (bilangan bulat 0-100), relatif
                   terhadap frekuensi terbesar di halaman ini (shelf_max).

    Contoh:
        serat dan natrium kosong, belum ada pengajuan
            -> {..., "status": "needs_contribution", "status_label": "Perlu kontribusi",
                "submit_url": "/antrean/produk/7/ajukan/?field=fiber_100g&field=sodium_100g",
                "detail_url": "/katalog/7/", "image_url": "https://images.openfoodfacts.org/..."}
    """
    empty = {field for entry in row["missing"] for field in entry["fields"]}
    fields = [name for name in CORRECTABLE_FIELDS if name in empty]
    submit_url = reverse("data_correction:submit", args=[row["pk"]])
    if fields:
        submit_url += "?" + urlencode([("field", name) for name in fields])
    status = NEEDS_VERIFICATION if row["pk"] in pending_ids else NEEDS_CONTRIBUTION
    return {
        **row,
        "status": status,
        "status_label": STATUS_LABELS[status],
        "submit_url": submit_url,
        "detail_url": reverse("product_catalog:product_detail", args=[row["pk"]]),
        "image_url": (images or {}).get(row["pk"], ""),
        "shelf_bar": round(100 * (row.get("shelf_count") or 0) / shelf_max) if shelf_max else 0,
    }


def contribution_stats(total, shelf_total=None):
    """Kartu statistik, dihitung dari data yang ada (tanpa angka karangan).

    - incomplete_products   : produk belum lengkap, tanpa filter (dari queue_products)
    - submitted_last_7_days : DataCorrection yang dibuat dalam 7 x 24 jam terakhir. Bukan
                              minggu kalender, karena TIME_ZONE masih UTC.
    - approved              : total item koreksi yang disetujui kurator
    - shelf_average         : rata-rata frekuensi shelf per produk antrean (termasuk yang 0),
                              dibulatkan 1 desimal; None kalau data shelf tidak tersedia

    Contoh: contribution_stats(347, 140) -> {"incomplete_products": 347, "submitted_last_7_days": 3,
                                             "approved": 12, "shelf_average": 0.4}
    """
    since = timezone.now() - timedelta(days=7)
    if shelf_total is None:
        shelf_average = None
    else:
        shelf_average = round(shelf_total / total, 1) if total else 0
    return {
        "incomplete_products": total,
        "submitted_last_7_days": DataCorrection.objects.filter(created_at__gte=since).count(),
        "approved": DataCorrectionItem.objects.filter(status=APPROVED).count(),
        "shelf_average": shelf_average,
    }