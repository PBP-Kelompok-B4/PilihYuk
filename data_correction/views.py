"""View Modul 4 (Antrean Data): fitur pengguna.

Notes:
- Ajukan koreksi, daftar "Pengajuan Saya", detail pengajuan, dan tarik
  pengajuan. Antrean kontribusi dan moderasi menyusul di tahap berikutnya.
- Hanya mengambil objek, memanggil services.py, lalu memilih bentuk
  balasan. Aturan bisnis ada di services.py dan validators.py, bentuk balasan di
  responses.py, dan tampilan form di forms.py.
- Setiap view melayani HTML dan JSON (NF-3). JSON dipilih kalau ada ?format=json atau
  header Accept berisi application/json (lihat responses.wants_json).
- Akses:
  - semua view di file ini wajib login (login_required_json: HTML diarahkan ke halaman
    masuk, JSON mendapat 401);
  - pengajuan selalu disaring dengan submitted_by=request.user. Id di URL hanya memilih
    objek; pengajuan milik orang lain dijawab 404, sama seperti yang tidak ada;
  - id pengguna tidak pernah diambil dari URL atau form.
- Rute (lihat urls.py):
      GET/POST  antrean/produk/<pk>/ajukan/   submit             form ajukan koreksi
      GET       antrean/saya/                 my_corrections     daftar pengajuan sendiri
      GET       antrean/saya/<pk>/            correction_detail  detail (halaman sukses)
      POST      antrean/saya/<pk>/tarik/      withdraw           tarik pengajuan
"""
from functools import wraps

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import prefetch_related_objects
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from product_catalog.models import Product

from . import services
from .forms import CorrectionForm
from .models import DataCorrection
from .responses import json_error, json_ok, login_required_json, page_payload, render_or_json, wants_json
from .validators import to_column_value

PAGE_SIZE = 10  # pengajuan per halaman di "Pengajuan Saya"



def serialize_item(item):
    """Satu DataCorrectionItem untuk JSON. Nilai dalam satuan kolom (natrium gram).

    Contoh:
        {"field_name": "sodium_100g", "label": "Natrium (mg/100 g)", "old_value": null,
         "proposed_value": 0.78, "status": "pending", "status_label": "Menunggu",
         "review_note": ""}
    """
    return {
        "field_name": item.field_name,
        "label": item.get_field_name_display(),
        "old_value": to_column_value(item.field_name, item.old_value),
        "proposed_value": to_column_value(item.field_name, item.proposed_value),
        "status": item.status,
        "status_label": item.get_status_display(),
        "review_note": item.review_note,
    }


def serialize_correction(correction):
    """Satu DataCorrection untuk JSON (balasan ajukan, detail, dan daftar).
    Item diambil sekali saja: kalau belum di-prefetch, prefetch dilakukan di sini, jadi
    status turunan dan daftar item tidak memicu query berulang.

    Contoh:
        {"id": 12, "product": {"id": 7, "product_name": "Sarimi Isi 2 Goreng"},
         "status": "pending", "status_label": "Menunggu", "is_withdrawable": true,
         "created_at": "2026-10-22T08:04:00.123Z", "items": [{...}, {...}]}
    """
    prefetch_related_objects([correction], "items")
    return {
        "id": correction.pk,
        "product": {"id": correction.product_id, "product_name": correction.product.product_name},
        "status": correction.status,
        "status_label": correction.get_status_display(),
        "is_withdrawable": correction.is_withdrawable,
        "created_at": correction.created_at,
        "items": [serialize_item(item) for item in correction.items.all()],
    }


def _json_404(error_id, message):
    """Decorator: Http404 dari get_object_or_404 menjadi JSON 404 untuk klien JSON.
    Permintaan HTML tetap mendapat halaman 404 bawaan Django.

    Contoh:
        @_json_404("product_not_found", "Produk tidak ditemukan.")
        GET /antrean/produk/999/ajukan/?format=json
            -> 404 {"error": {"id": "product_not_found", "message": "Produk tidak ditemukan."}}
    """
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            try:
                return view(request, *args, **kwargs)
            except Http404:
                if wants_json(request):
                    return json_error(message, status=404, error_id=error_id)
                raise
        return wrapped
    return decorator


@login_required_json
@require_http_methods(["GET", "POST"])
@_json_404("product_not_found", "Produk tidak ditemukan.")
def submit(request, pk):
    """Form ajukan koreksi untuk satu produk aktif (PRD F-4.1 sampai F-4.3).

    GET  : form beserta nilai saat ini. ?field=proteins_100g menandai kotak protein
           (boleh diulang). JSON: daftar field koreksi dan nilai saat ini.
    POST : berhasil -> HTML diarahkan ke halaman detail dengan pesan sukses, JSON 201.
           gagal    -> HTML form dengan pesan error, JSON 400 dengan pesan per field.

    Contoh:
        POST /antrean/produk/7/ajukan/  proteins_100g=8,5&sodium_100g=780
            -> 302 ke /antrean/saya/12/?terkirim=1
        POST /antrean/produk/7/ajukan/?format=json  nova_group=5
            -> 400 {"error": {...}, "fields": {"nova_group": [{"message": "Grup NOVA ..."}]}}
    """
    product = get_object_or_404(Product, pk=pk, is_active=True)
    form = CorrectionForm(
        request.POST if request.method == "POST" else None,
        product=product,
        focus=request.GET.getlist("field"),
    )
    status = 200
    if request.method == "POST":
        try:
            correction = services.submit_correction(request.user, product, form.changes())
        except services.CorrectionError as error:
            if wants_json(request):
                return json_error(error.message, error.fields, error.status, error.error_id)
            form.add_correction_error(error)
            status = error.status
        else:
            if wants_json(request):
                return json_ok(serialize_correction(correction), status=201)
            messages.success(request, "Pengajuan koreksi terkirim dan menunggu tinjauan kurator.")
            detail_url = reverse("data_correction:correction_detail", args=[correction.pk])
            return redirect(f"{detail_url}?terkirim=1")
    return render_or_json(
        request,
        "data_correction/submit.html",
        {"product": product, "form": form},
        lambda: {
            "product": {"id": product.pk, "product_name": product.product_name},
            "correctable_fields": form.json_fields(),
        },
        status=status,
    )


@login_required_json
@require_safe
def my_corrections(request):
    """Daftar pengajuan milik pengguna yang sedang masuk, terbaru dulu, 10 per halaman.
    Produk diambil dengan select_related dan item dengan prefetch_related, jadi jumlah
    query tetap walaupun pengajuannya banyak.

    Contoh:
        GET /antrean/saya/?page=2&format=json
            -> {"count": 14, "page": 2, "page_size": 10, "results": [{...}, ...]}
    """
    corrections = (
        DataCorrection.objects.filter(submitted_by=request.user)
        .select_related("product")
        .prefetch_related("items")
        .order_by("-created_at", "-pk")
    )
    page = Paginator(corrections, PAGE_SIZE).get_page(request.GET.get("page"))
    return render_or_json(
        request,
        "data_correction/my_corrections.html",
        {"page_obj": page},
        lambda: page_payload(page, [serialize_correction(correction) for correction in page]),
    )


@login_required_json
@require_safe
@_json_404("correction_not_found", "Pengajuan tidak ditemukan.")
def correction_detail(request, pk):
    """Detail satu pengajuan milik sendiri; juga dipakai sebagai halaman sukses.
    ?terkirim=1 (dari redirect setelah mengajukan) menampilkan judul "berhasil dikirim".

    Contoh:
        GET /antrean/saya/12/                      -> 200 (milik sendiri)
        GET /antrean/saya/13/                      -> 404 (milik orang lain)
        GET /antrean/saya/13/?format=json          -> 404 {"error": {"id": "correction_not_found", ...}}
    """
    correction = get_object_or_404(
        DataCorrection.objects.select_related("product").prefetch_related("items"),
        pk=pk,
        submitted_by=request.user,
    )
    return render_or_json(
        request,
        "data_correction/submit_success.html",
        {"correction": correction, "just_submitted": request.GET.get("terkirim") == "1"},
        lambda: serialize_correction(correction),
    )



@login_required_json
@require_POST
@_json_404("correction_not_found", "Pengajuan tidak ditemukan.")
def withdraw(request, pk):
    """Tarik (hapus) pengajuan sendiri selama belum ada item yang ditinjau (PRD F-4.5).

    Contoh:
        POST /antrean/saya/12/tarik/?format=json  -> 200 {"deleted": true, "id": 12}
        POST /antrean/saya/12/tarik/              -> 302 ke /antrean/saya/ + pesan sukses
        sudah ada item ditinjau                   -> JSON 409 not_withdrawable,
                                                     HTML 302 ke /antrean/saya/ + pesan error
        milik orang lain                          -> 404
    """
    correction = get_object_or_404(DataCorrection, pk=pk, submitted_by=request.user)
    try:
        deleted_pk = services.withdraw_correction(request.user, correction)
    except services.CorrectionError as error:
        if wants_json(request):
            return json_error(error.message, error.fields, error.status, error.error_id)
        messages.error(request, error.message)
    else:
        if wants_json(request):
            return json_ok({"deleted": True, "id": deleted_pk})
        messages.success(request, "Pengajuan berhasil ditarik.")
    return redirect("data_correction:my_corrections")