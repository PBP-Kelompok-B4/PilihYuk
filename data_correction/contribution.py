"""Antrean kontribusi di /antrean/ (PRD F-4.7): produk aktif yang datanya belum lengkap.

Notes:
- Aturan "belum lengkap" TIDAK ditulis ulang di sini. Semuanya dari incomplete.py
  (incomplete_products dan CATEGORIES); file ini hanya menyaring, mengurutkan, menghitung
  status dan statistik, lalu menyusun tautan.

Daftar isi:
1. ContributionFilters : membaca ?sort=, ?missing=, ?page= dan menyusun URL antrean.
2. queue_products, sort_rows : produk belum lengkap, sudah disaring dan diurutkan.
3. pending_product_ids, decorate : status per produk, tautan "Lengkapi Data" dan "Detail".
4. contribution_stats : kartu statistik.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone

from product_catalog.models import Product

from .constants import APPROVED, CORRECTABLE_FIELDS, PENDING
from .incomplete import CATEGORIES, incomplete_products
from .models import DataCorrection, DataCorrectionItem

SORTS = (
    ("kosong", "Paling banyak data kosong"),
    ("terbaru", "Terbaru"),
)
DEFAULT_SORT = SORTS[0][0]
SHELF_SORT = "shelf"  # "Paling sering muncul di shelf", bonus Tahap 10 (butuh ShelfItem)

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
            -> ContributionFilters(sort="terbaru", missing="nova", page="")
        ContributionFilters.from_query({"sort": "acak", "missing": "code"})
            -> ContributionFilters(sort="kosong", missing="", page="")
        ContributionFilters.from_query({"sort": "shelf"})
            -> ContributionFilters(sort="kosong", ...)   (sampai Tahap 10)
    """

    sort: str = DEFAULT_SORT
    missing: str = ""  # key kategori dari incomplete.CATEGORIES, kosong = semua
    page: str = ""

    @classmethod
    def from_query(cls, query):
        sort = query.get("sort", "")
        if sort == SHELF_SORT:
            sort = DEFAULT_SORT
        missing = query.get("missing", "")
        return cls(
            sort=sort if sort in dict(SORTS) else DEFAULT_SORT,
            missing=missing if missing in CATEGORY_LABELS else "",
            page=query.get("page", ""),
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
        if values["sort"] == DEFAULT_SORT:
            values["sort"] = ""
        query = urlencode({key: value for key, value in values.items() if value not in ("", None)})
        base = reverse("data_correction:contribution_queue")
        return f"{base}?{query}" if query else base

    def sort_chips(self):
        """Chip "Urutkan:". Mengganti urutan kembali ke halaman 1, filter tetap."""
        return [
            {"label": label, "url": self.url(sort=key, page=""), "active": key == self.sort}
            for key, label in SORTS
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
        """URL halaman sebelum dan sesudah (None kalau tidak ada), dengan filter yang sama.

        Contoh (halaman 2 dari 3): {"previous": "/antrean/?page=1", "next": "/antrean/?page=3"}
        """
        return {
            "previous": self.url(page=page.previous_page_number()) if page.has_previous() else None,
            "next": self.url(page=page.next_page_number()) if page.has_next() else None,
        }


def queue_products(filters):
    """Semua produk belum lengkap, sudah disaring ?missing= dan diurutkan ?sort=.

    Contoh (data seed, misc_tags kosong):
        queue_products(ContributionFilters(missing="nova"))
            -> ([186 baris yang kurang NOVA], ["nutrition", "nova", "brand", "quantity", "origin"], 347)
    """
    rows = incomplete_products()  # satu query; produk nonaktif sudah dibuang
    present = {entry["key"] for row in rows for entry in row["missing"]}
    categories = [key for key, _, _ in CATEGORIES if key in present]
    total = len(rows)
    if filters.missing:
        rows = [row for row in rows if any(entry["key"] == filters.missing for entry in row["missing"])]
    return sort_rows(rows, filters.sort), categories, total


def sort_rows(rows, sort):
    """Urutkan baris antrean. Pengurutan Python stabil, jadi urutan nama A-Z dipasang dulu
    sebagai pemecah seri, lalu diurutkan ulang dengan kunci utamanya.

    Contoh:
        [Bihun (1 kurang), apel kering (1), Zebra (2)], "kosong"  -> [Zebra, apel kering, Bihun]
    """
    rows = sorted(rows, key=lambda row: ((row["product_name"] or "").casefold(), row["pk"]))
    if sort == "terbaru":
        added = dict(Product.objects.values_list("pk", "created_at"))
        return sorted(rows, key=lambda row: added.get(row["pk"], OLDEST), reverse=True)
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


def decorate(row, pending_ids):
    """Satu baris siap tampil: tambah status, status_label, submit_url, dan detail_url.

    - status     : "needs_verification" kalau produk sudah punya item pending,
                   selain itu "needs_contribution".
    - submit_url : ?field= untuk SETIAP field kosong yang bisa dikoreksi, urut seperti form
                   (CORRECTABLE_FIELDS), jadi kotak kosong pertama mendapat autofocus.
                   Produk yang hanya punya kategori informasi mendapat URL tanpa ?field=.
                   Pengunjung yang membukanya diarahkan ke halaman masuk oleh view submit.
    - detail_url : halaman produk di katalog (product_catalog:product_detail).

    Contoh:
        serat dan natrium kosong, belum ada pengajuan
            -> {..., "status": "needs_contribution", "status_label": "Perlu kontribusi",
                "submit_url": "/antrean/produk/7/ajukan/?field=fiber_100g&field=sodium_100g",
                "detail_url": "/katalog/7/"}
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
    }


def contribution_stats(total):
    """Kartu statistik, dihitung dari data yang ada (tanpa angka karangan).

    - incomplete_products   : produk belum lengkap, tanpa filter (dari queue_products)
    - submitted_last_7_days : DataCorrection yang dibuat dalam 7 x 24 jam terakhir. Bukan
                              minggu kalender, karena TIME_ZONE masih UTC.
    - approved              : total item koreksi yang disetujui kurator

    Contoh: contribution_stats(347) -> {"incomplete_products": 347, "submitted_last_7_days": 3,
                                        "approved": 12}
    """
    since = timezone.now() - timedelta(days=7)
    return {
        "incomplete_products": total,
        "submitted_last_7_days": DataCorrection.objects.filter(created_at__gte=since).count(),
        "approved": DataCorrectionItem.objects.filter(status=APPROVED).count(),
    }