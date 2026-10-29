"""Antrean kurator di /moderasi/ (PRD F-4.4): filter, daftar item, statistik, panduan field.

Notes:
- Logika data halaman moderasi dikumpulkan di sini, tanpa urusan HTTP, supaya view
  curator_queue tetap tipis
- Satu baris antrean = satu DataCorrectionItem, karena kurator meninjau per field.

Daftar isi:
1. QueueFilters : membaca ?tab=, ?field=, ?status=, ?page= dan menyusun URL antrean.
2. queue_items, find_item : item sesuai filter; produk dan pengaju ikut diambil (tanpa N+1).
3. queue_stats  : total item per status dalam satu query.
4. queue_row    : satu baris siap tampil (nilai saat ini, penanda berubah, tautan).
5. field_guide  : isi tab "Panduan field", dibangun dari constants dan validators.
"""
from dataclasses import dataclass
from urllib.parse import urlencode

from django.db.models import Count, Q
from django.urls import reverse

from .constants import (
    APPROVED,
    CORRECTABLE_FIELDS,
    DISPLAY_FACTORS,
    FIELD_LABELS,
    INTEGER_FIELDS,
    PENDING,
    REJECTED,
    STATUS_CHOICES,
    TEXT_FIELDS,
)
from .display import display_name
from .forms import help_text_for
from .models import DataCorrectionItem
from .validators import (
    DEFAULT_MAX_DISPLAY_VALUE,
    DISPLAY_UNITS,
    MAX_DECIMAL_PLACES,
    MAX_DISPLAY_VALUES,
    get_current_value,
)

TABS = (
    ("antrean", "Antrean koreksi"),
    ("semua", "Semua pengajuan"),
    ("panduan", "Panduan field"),
)
DEFAULT_TAB = TABS[0][0]
STATUS_LABELS = dict(STATUS_CHOICES)  # "pending" -> "Menunggu", dst.


@dataclass(frozen=True)
class QueueFilters:
    """Keadaan halaman antrean yang dibaca dari query string.

    Contoh:
        QueueFilters.from_query({"tab": "semua", "status": "rejected"})
            -> QueueFilters(tab="semua", field="", status="rejected", page="")
        QueueFilters.from_query({"tab": "riwayat", "field": "code"})
            -> QueueFilters(tab="antrean", field="", status="", page="")
    """

    tab: str = DEFAULT_TAB
    field: str = ""
    status: str = ""  # hanya berlaku di tab "semua"
    page: str = ""

    @classmethod
    def from_query(cls, query):
        tab = query.get("tab", "")
        tab = tab if tab in dict(TABS) else DEFAULT_TAB
        field = query.get("field", "")
        status = query.get("status", "")
        return cls(
            tab=tab,
            field=field if field in CORRECTABLE_FIELDS else "",
            status=status if tab == "semua" and status in STATUS_LABELS else "",
            page=query.get("page", ""),
        )

    def url(self, **changes):
        """URL /moderasi/ dengan filter sekarang; sebagian bisa diganti lewat argumen.
        Nilai kosong dan tab bawaan tidak ditulis, jadi URL tetap pendek.

        Contoh (filter sekarang: tab "semua", field "fiber_100g"):
            url()          -> "/moderasi/?tab=semua&field=fiber_100g"
            url(page=2)    -> "/moderasi/?tab=semua&field=fiber_100g&page=2"
            url(item=15)   -> "/moderasi/?tab=semua&field=fiber_100g&item=15"
            url(field="")  -> "/moderasi/?tab=semua"
        """
        values = {"tab": self.tab, "field": self.field, "status": self.status, "page": self.page, **changes}
        if values["tab"] == DEFAULT_TAB:
            values["tab"] = ""
        query = urlencode({key: value for key, value in values.items() if value not in ("", None)})
        base = reverse("data_correction:queue")
        return f"{base}?{query}" if query else base

    def tabs(self):
        return [
            {"label": label, "url": QueueFilters(tab=key).url(), "active": key == self.tab}
            for key, label in TABS
        ]

    def field_chips(self):
        chips = [{"label": "Semua field", "url": self.url(field="", page=""), "active": not self.field}]
        chips += [
            {"label": FIELD_LABELS[name], "url": self.url(field=name, page=""), "active": name == self.field}
            for name in CORRECTABLE_FIELDS
        ]
        return chips

    def status_chips(self):
        if self.tab != "semua":
            return []
        chips = [{"label": "Semua status", "url": self.url(status="", page=""), "active": not self.status}]
        chips += [
            {"label": label, "url": self.url(status=key, page=""), "active": key == self.status}
            for key, label in STATUS_CHOICES
        ]
        return chips

    def page_links(self, page):
        """URL halaman sebelum dan sesudah (None kalau tidak ada), dengan filter yang sama.

        Contoh (halaman 2 dari 3): {"previous": "/moderasi/?page=1", "next": "/moderasi/?page=3"}
        """
        return {
            "previous": self.url(page=page.previous_page_number()) if page.has_previous() else None,
            "next": self.url(page=page.next_page_number()) if page.has_next() else None,
        }


ITEM_RELATIONS = ("correction__product", "correction__submitted_by")


def queue_items(filters):
    """Item untuk tab antrean atau semua, sesuai filter.

    Contoh:
        queue_items(QueueFilters())                              -> item pending, terlama dulu
        queue_items(QueueFilters(field="fiber_100g"))            -> hanya item serat
        queue_items(QueueFilters(tab="semua", status="rejected")) -> item ditolak, terbaru dulu
    """
    items = DataCorrectionItem.objects.select_related(*ITEM_RELATIONS)
    if filters.field:
        items = items.filter(field_name=filters.field)
    if filters.tab == "semua":
        if filters.status:
            items = items.filter(status=filters.status)
        return items.order_by("-correction__created_at", "-correction_id", "pk")
    return items.filter(status=PENDING).order_by("correction__created_at", "correction_id", "pk")


def find_item(item_id):
    """Satu item (beserta produk dan pengaju) untuk panel review, atau None.

    Contoh:
        find_item("15")   -> <DataCorrectionItem 15>
        find_item("abc")  -> None
        find_item("999")  -> None   (tidak ada, mis. pengajuannya sudah ditarik)
    """
    item_id = str(item_id)
    if not item_id.isdecimal():
        return None
    return DataCorrectionItem.objects.select_related(*ITEM_RELATIONS).filter(pk=int(item_id)).first()


def queue_stats():
    """Total item per status, dihitung langsung dari database dalam satu query.
    Tidak ada angka "hari ini" (lihat CATATAN di atas).

    Contoh: {"pending": 24, "approved": 12, "rejected": 3}
    """
    return DataCorrectionItem.objects.aggregate(
        pending=Count("pk", filter=Q(status=PENDING)),
        approved=Count("pk", filter=Q(status=APPROVED)),
        rejected=Count("pk", filter=Q(status=REJECTED)),
    )


def queue_row(item, filters):
    """Satu baris antrean, siap untuk template dan JSON.

    - current : nilai kolom Product SEKARANG dalam bentuk teks simpanan (None = tidak
                diketahui). Template menampilkannya lewat filter display_value.
    - stale   : True kalau item masih pending dan nilai produk sudah berubah sejak
                diajukan (beda dengan old_value). Menyetujui akan menimpa nilai baru itu.

    Contoh:
        {"item": <item serat>, "product": <Sarimi>, "submitter": "Budi",
         "current": None, "stale": False, "url": "/moderasi/?item=15"}
    """
    product = item.correction.product
    current = get_current_value(product, item.field_name)
    return {
        "item": item,
        "product": product,
        "submitter": display_name(item.correction.submitted_by),
        "current": current,
        "stale": item.status == PENDING and current != item.old_value,
        "url": filters.url(item=item.pk),
    }


def field_guide():
    """Isi tab "Panduan field": semua field koreksi beserta aturan validasinya.

    Contoh satu elemen:
        {"field_name": "sodium_100g", "label": "Natrium (mg/100 g)", "kind": "Angka desimal",
         "rules": ["Angka dalam mg per 100 g, tanpa pemisah ribuan. Contoh: 780.",
                   "Rentang 0 sampai 100000 mg per 100 g, paling banyak 3 angka di belakang koma.",
                   "Diisi dalam mg; produk menyimpannya dalam gram (dibagi 1000)."]}
    """
    guide = []
    for name in CORRECTABLE_FIELDS:
        rules = [help_text_for(name)]
        if name in TEXT_FIELDS:
            kind = "Teks"
            rules.append("Spasi berlebih dirapikan otomatis; teks kosong tidak bisa diajukan.")
        elif name in INTEGER_FIELDS:
            kind = "Bilangan bulat"
        else:
            kind = "Angka desimal"
            unit = DISPLAY_UNITS.get(name, "g")
            limit = MAX_DISPLAY_VALUES.get(name, DEFAULT_MAX_DISPLAY_VALUE)
            rules.append(
                f"Rentang 0 sampai {limit} {unit} per 100 g, "
                f"paling banyak {MAX_DECIMAL_PLACES} angka di belakang koma."
            )
            if name in DISPLAY_FACTORS:
                rules.append(
                    f"Diisi dalam {unit}; produk menyimpannya dalam gram (dibagi {DISPLAY_FACTORS[name]})."
                )
        guide.append({"field_name": name, "label": FIELD_LABELS[name], "kind": kind, "rules": rules})
    return guide