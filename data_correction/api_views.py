"""API Django REST Framework Modul Antrean Data untuk aplikasi Flutter.

Notes:
- Pola mengikuti accounts/api_views.py dan konvensi API di .ai/timeline.md: @api_view,
  @authentication_classes([SessionAuthentication]), @permission_classes, tanpa @csrf_exempt.
  SessionAuthentication hanya memeriksa token CSRF untuk metode yang mengubah data, jadi GET
  dari pbp_django_auth (yang tidak mengirim token CSRF) tetap lolos. POST dari aplikasi
  memakai sendJson di lib/api.dart, yang mengirim token dari cookie csrftoken.
- Aturan TIDAK ditulis ulang di sini. View hanya membaca permintaan, memanggil fungsi yang
  sama dengan halaman web, lalu memilih bentuk balasan:
  - antrean: contribution.py (filter, urutan, status, statistik), incomplete.py, shelf_frequency.py;
  - form dan pengajuan: forms.CorrectionForm dan services.submit_correction (validasi lewat
    validators.py). Jadi hasil di aplikasi selalu sama dengan hasil di situs web.
- Bentuk galat modul (KEPUTUSAN TAHAP 0 bagian C):
      {"detail": "<pesan>", "code": "<error_id>", "fields": {"<nama>": ["<pesan>"]}}
  "fields" hanya untuk galat isian. CorrectionError diubah menjadi balasan ini oleh decorator
  correction_errors. Galat bawaan DRF (403 belum masuk atau CSRF, 405, JSON rusak) tetap
  {"detail": "..."} tanpa code.
- Identitas pengaju tidak pernah dikirim (F-4.9). Pengaju pengajuan baru selalu request.user.
- Daftar endpoint modul ini ada di api_urls.py.

Daftar isi:
1. Helper     : error_body, correction_errors, shape_errors (+ _messages), active_product
2. Antrean    : contribution_queue_data, contribution_queue
3. Pengajuan  : correction_form, my_corrections
"""
from functools import wraps

from django.core.paginator import Paginator
from django.db.models import prefetch_related_objects
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from product_catalog.models import Product

from . import contribution, services, shelf_frequency
from .forms import GROUPS, CorrectionForm
from .serializers import (
    ContributionQueueSerializer,
    CorrectionFormSerializer,
    CorrectionSerializer,
    CorrectionSubmitSerializer,
)
from .services import CorrectionError
from .validators import to_display
from .views import CONTRIBUTION_PAGE_SIZE  # 20, sama dengan halaman web

# Pesan umum galat isian, sama dengan pesan services.submit_correction.
INVALID_MESSAGE = "Periksa kembali isian koreksi."
# Judul kelompok per field dari forms.GROUPS, mis. "brand" -> "Info produk".
GROUP_TITLES = {name: title for title, names in GROUPS for name in names}


# ===== 1. Helper =====


def error_body(error):
    """CorrectionError -> body JSON galat modul.

    Contoh:
        CorrectionError("product_not_found", "Produk tidak ditemukan.", 404)
            -> {"detail": "Produk tidak ditemukan.", "code": "product_not_found"}
        CorrectionError("validation_error", "Periksa kembali isian koreksi.",
                        fields={"nova_group": ["Grup NOVA harus bilangan bulat 1 sampai 4."]})
            -> {"detail": "Periksa kembali isian koreksi.", "code": "validation_error",
                "fields": {"nova_group": ["Grup NOVA harus bilangan bulat 1 sampai 4."]}}
    """
    body = {"detail": error.message, "code": error.error_id}
    if error.fields:
        body["fields"] = {
            str(name): [str(message) for message in messages] for name, messages in error.fields.items()
        }
    return body


def correction_errors(view):
    """Decorator: CorrectionError dari view atau services menjadi Response galat modul dengan
    status dari error itu. Dipasang paling bawah, tepat di atas def view.

    Contoh:
        services.submit_correction melempar CorrectionError("validation_error", ..., 400)
            -> Response(error_body(error), status=400)
    """

    @wraps(view)  # menjaga nama dan docstring, yang juga tampil di Browsable API
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except CorrectionError as error:
            return Response(error_body(error), status=error.status)

    return wrapped


def shape_errors(errors):
    """Galat bentuk dari serializer DRF (bisa bersarang) -> {kunci body: [pesan, ...]}.
    DRF menandai baris items yang salah dengan nomor indeks (mulai 0); di sini ditulis
    "Baris <n>" mulai 1.

    Contoh:
        {"product": ["Bidang ini harus diisi."]}
            -> {"product": ["Bidang ini harus diisi."]}
        {"items": {"non_field_errors": ["Expected a list of items ..."]}}   (items bukan daftar)
            -> {"items": ["Expected a list of items ..."]}
        {"items": {1: {"field_name": ["Bidang ini harus diisi."]}}}         (baris kedua salah)
            -> {"items": ["Baris 2, field_name: Bidang ini harus diisi."]}
    """
    return {str(name): _messages(value) for name, value in errors.items()}


def _messages(value, where=""):
    """Isi galat bersarang -> daftar teks, dengan lokasinya di depan pesan.

    Contoh:
        [ErrorDetail("Bidang ini harus diisi.")]          -> ["Bidang ini harus diisi."]
        {0: {"field_name": ["Bidang ini harus diisi."]}}  -> ["Baris 1, field_name: Bidang ini harus diisi."]
    """
    if isinstance(value, dict):
        messages = []
        for key, inner in value.items():
            if key == "non_field_errors":
                messages += _messages(inner, where)
            elif isinstance(key, int):
                messages += _messages(inner, f"{where}Baris {key + 1}, ")
            else:
                messages += _messages(inner, f"{where}{key}: ")
        return messages
    if isinstance(value, list):
        return [message for inner in value for message in _messages(inner, where)]
    return [f"{where}{value}"]


def active_product(pk):
    """Produk aktif, sama dengan get_object_or_404(Product, pk=pk, is_active=True) di
    views.submit, tetapi 404-nya berbentuk galat modul.

    Contoh:
        active_product(7)            -> <Product 7>
        active_product(999)          -> CorrectionError("product_not_found", "Produk tidak ditemukan.", 404)
        active_product(<nonaktif>)   -> CorrectionError yang sama
    """
    try:
        return get_object_or_404(Product, pk=pk, is_active=True)
    except Http404:
        raise CorrectionError("product_not_found", "Produk tidak ditemukan.", 404) from None


# ===== 2. Antrean kontribusi =====


def contribution_queue_data(query):
    """Satu halaman antrean kontribusi sebagai dict untuk ContributionQueueSerializer.
    Langkahnya sama dengan views.contribution_queue, dengan jumlah query tetap
    (6, atau 7 untuk ?sort=terbaru) berapa pun jumlah produknya.

    Argumen:
        query : request.query_params (?sort=, ?missing=, ?page=)

    Contoh (data seed + data demo):
        contribution_queue_data({"missing": "nova", "page": "2"})
            -> {"count": 186, "page": 2, "page_size": 20, "num_pages": 10, "next_page": 3,
                "previous_page": 1, "sort": "shelf", "missing": "nova", ...}
    """
    frequency = shelf_frequency.shelf_counts()  # satu query untuk semua produk
    filters = contribution.ContributionFilters.from_query(query, frequency.available)
    queue = contribution.queue_products(filters, frequency)
    page = Paginator(queue.rows, CONTRIBUTION_PAGE_SIZE).get_page(filters.page)
    product_ids = [row["pk"] for row in page]
    pending = contribution.pending_product_ids(product_ids)
    images = contribution.page_images(product_ids)
    return {
        "count": page.paginator.count,
        "page": page.number,
        "page_size": page.paginator.per_page,
        "num_pages": page.paginator.num_pages,
        "next_page": page.next_page_number() if page.has_next() else None,
        "previous_page": page.previous_page_number() if page.has_previous() else None,
        "sort": filters.sort,
        "missing": filters.missing or None,
        "shelf_available": frequency.available,
        "sort_options": [{"key": key, "label": label} for key, label in filters.sorts],
        "missing_options": [
            {"key": key, "label": contribution.CATEGORY_LABELS[key]} for key in queue.categories
        ],
        "stats": contribution.contribution_stats(queue.total, queue.shelf_total),
        "results": [contribution.decorate(row, pending, images) for row in page],
    }


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def contribution_queue(request):
    """Antrean kontribusi: produk aktif yang datanya belum lengkap (PRD F-4.7). PUBLIK.

    Query string (sama dengan /antrean/; nilai tidak dikenal kembali ke bawaan):
        ?sort=shelf (bawaan) | kosong | terbaru   tanpa data shelf, bawaannya kosong
        ?missing=<key kategori>                   mis. nutrition, nova, brand, quantity, origin
        ?page=<n>                                 20 produk per halaman; bukan angka -> 1,
                                                  lewat dari halaman terakhir -> terakhir

    Contoh:
        GET /api/v1/corrections/queue/
        GET /api/v1/corrections/queue/?missing=nova&sort=terbaru&page=2
        POST /api/v1/corrections/queue/  -> 405 (sudah login tanpa token CSRF: 403)
    """
    return Response(ContributionQueueSerializer(contribution_queue_data(request.query_params)).data)


# ===== 3. Form dan pengajuan =====


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@correction_errors
def correction_form(request, pk):
    """Field koreksi beserta nilai saat ini untuk satu produk aktif (cermin GET
    antrean/produk/<pk>/ajukan/). Wajib masuk.

    Query string:
        ?field=<nama field>   boleh berulang, sama dengan submit_url di web. Menjadi "focus"
                              (baris awal form); nama yang tidak dikenal atau ganda diabaikan.

    Contoh:
        GET /api/v1/corrections/products/7/form/?field=fiber_100g&field=sodium_100g
            -> 200 {"product": {"id": 7, "product_name": "Sarimi Isi 2 Goreng", ...},
                    "focus": ["fiber_100g", "sodium_100g"],
                    "correctable_fields": [
                        {"field_name": "product_name", "label": "Nama produk", "group": "Info produk",
                         "type": "text", "current_value": "Sarimi Isi 2 Goreng", ...},
                        ...,
                        {"field_name": "sodium_100g", "label": "Natrium (mg/100 g)",
                         "group": "Gizi per 100 g", "type": "number", "current_value": 0.3976,
                         "current_display": "397,6", "display_factor": 1000, ...}]}
        GET /api/v1/corrections/products/999/form/
            -> 404 {"detail": "Produk tidak ditemukan.", "code": "product_not_found"}
        tanpa masuk -> 403
    """
    product = active_product(pk)
    form = CorrectionForm(None, product=product, focus=request.query_params.getlist("field"))
    fields = [
        {
            **field,
            "group": GROUP_TITLES[field["field_name"]],
            "current_display": to_display(field["field_name"], field["current_value"]),
        }
        for field in form.json_fields()
    ]
    data = {"product": product, "focus": form.focus, "correctable_fields": fields}
    return Response(CorrectionFormSerializer(data).data)


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@correction_errors
def my_corrections(request):
    """Ajukan koreksi untuk satu produk aktif (PRD F-4.1 sampai F-4.3), cermin POST
    antrean/produk/<pk>/ajukan/. Wajib masuk dan wajib token CSRF. GET (daftar pengajuan
    sendiri) menyusul di endpoint yang sama.

    Body JSON (bentuk diperiksa CorrectionSubmitSerializer, isi dinilai services.submit_correction):
        {"product": 7, "items": [{"field_name": "proteins_100g", "proposed_value": "8,5"},
                                 {"field_name": "sodium_100g", "proposed_value": "780"}]}
    - items dikirim sebagai daftar pasangan, jadi field yang diajukan dua kali terdeteksi.
    - Natrium diisi dalam mg dan disimpan dalam gram.
    - Pengaju selalu request.user; kunci lain di body (mis. submitted_by) diabaikan.

    Contoh:
        body di atas
            -> 201 {"id": 12, "product": {...}, "status": "pending", "status_label": "Menunggu",
                    "is_withdrawable": true, "created_at": "...", "items": [
                        {"field_name": "proteins_100g", ..., "proposed_value": 8.5, ...},
                        {"field_name": "sodium_100g", ..., "proposed_value": 0.78,
                         "proposed_display": "780", ...}]}
        {"product": 7, "items": [{"field_name": "nova_group", "proposed_value": "5"}]}
            -> 400 {"detail": "Periksa kembali isian koreksi.", "code": "validation_error",
                    "fields": {"nova_group": ["Grup NOVA harus bilangan bulat 1 sampai 4."]}}
        {"product": 7, "items": []}
            -> 400 {"detail": "Pilih minimal satu field untuk dikoreksi.", "code": "validation_error"}
        {"product": 999, "items": [...]}
            -> 404 {"detail": "Produk tidak ditemukan.", "code": "product_not_found"}
        tanpa token CSRF -> 403
    """
    body = CorrectionSubmitSerializer(data=request.data)
    if not body.is_valid():
        raise CorrectionError("validation_error", INVALID_MESSAGE, fields=shape_errors(body.errors))
    product = active_product(body.validated_data["product"])
    changes = [(item["field_name"], item["proposed_value"]) for item in body.validated_data["items"]]
    correction = services.submit_correction(request.user, product, changes)
    prefetch_related_objects([correction], "items")  # satu query untuk semua item
    return Response(CorrectionSerializer(correction).data, status=status.HTTP_201_CREATED)