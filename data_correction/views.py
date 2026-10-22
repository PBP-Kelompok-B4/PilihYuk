"""View Modul 4 (Antrean Data): fitur pengguna dan kurator.

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
      GET       moderasi/                     curator_queue      antrean kurator (nama: queue)
      POST      moderasi/item/<pk>/tinjau/    review_item        setujui/tolak satu item
"""
from functools import wraps

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import prefetch_related_objects
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from product_catalog.models import Product

from . import moderation, services
from .constants import APPROVED
from .forms import APPROVE, CorrectionForm, ReviewForm
from .models import DataCorrection, DataCorrectionItem
from .responses import (
    json_error,
    json_ok,
    login_required_json,
    page_payload,
    render_or_json,
    staff_required,
    wants_json,
)
from .validators import get_current_value, to_column_value

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

QUEUE_PAGE_SIZE = 20  # item per halaman di /moderasi/


def serialize_queue_row(row):
    """Satu baris antrean kurator untuk JSON. Nilai dalam satuan kolom (natrium gram).
    Bagian item memakai serialize_item yang sama dengan JSON pengguna (Tahap 4).

    Contoh:
        {"id": 15, "correction_id": 7,
         "product": {"id": 6, "product_name": "Sarimi isi 2 Goreng Ayam Kremes",
                     "brand": "Sarimi Isi 2", "quantity": "125g", "is_active": true},
         "submitted_by": "Budi", "created_at": "2026-10-22T02:15:00.000Z",
         "field_name": "fiber_100g", "label": "Serat (g/100 g)", "old_value": null,
         "proposed_value": 2.5, "status": "pending", "status_label": "Menunggu",
         "review_note": "", "current_value": null, "stale": false}
    """
    item, product = row["item"], row["product"]
    return {
        "id": item.pk,
        "correction_id": item.correction_id,
        "product": {
            "id": product.pk,
            "product_name": product.product_name,
            "brand": product.brand,
            "quantity": product.quantity,
            "is_active": product.is_active,
        },
        "submitted_by": row["submitter"],
        "created_at": item.correction.created_at,
        **serialize_item(item),
        "current_value": to_column_value(item.field_name, row["current"]),
        "stale": row["stale"],
    }


@staff_required
@require_safe
def curator_queue(request):
    """Antrean kurator: satu baris per item koreksi (PRD F-4.4). Khusus is_staff.

    Query string:
        ?tab=antrean (bawaan) | semua | panduan
        ?field=<nama field>   filter field (nama asing diabaikan)
        ?status=<status>      filter status, hanya di tab semua
        ?page=<n>             paginasi, 20 item per halaman
        ?item=<id item>       membuka panel review (HTML saja)

    Contoh:
        GET /moderasi/                              -> item pending, terlama dulu
        GET /moderasi/?tab=semua&status=rejected    -> item ditolak, terbaru dulu
        GET /moderasi/?field=fiber_100g&item=15     -> daftar item serat + panel item 15
        GET /moderasi/?format=json                  -> {"count", "page", "page_size", "results",
                                                        "tab", "field", "status", "stats"}
    """
    filters = moderation.QueueFilters.from_query(request.GET)
    stats = moderation.queue_stats()
    context = {"filters": filters, "stats": stats}

    if filters.tab == "panduan":
        context["guide"] = moderation.field_guide()
        return render_or_json(
            request, "data_correction/queue.html", context,
            lambda: {"tab": filters.tab, "stats": stats, "guide": context["guide"]},
        )

    page = Paginator(moderation.queue_items(filters), QUEUE_PAGE_SIZE).get_page(filters.page)
    rows = [moderation.queue_row(item, filters) for item in page]
    item_id = request.GET.get("item", "")
    selected = moderation.find_item(item_id) if item_id else None
    context.update({
        "page_obj": page,
        "rows": rows,
        "page_links": filters.page_links(page),
        "selected": moderation.queue_row(selected, filters) if selected else None,
        "missing_item": bool(item_id) and selected is None,
        "review_form": ReviewForm(),
        "back_url": filters.url(),  
    })
    return render_or_json(
        request, "data_correction/queue.html", context,
        lambda: {
            **page_payload(page, [serialize_queue_row(row) for row in rows]),
            "tab": filters.tab,
            "field": filters.field or None,
            "status": filters.status or None,
            "stats": stats,
        },
    )


def serialize_review(result):
    """Hasil tinjau untuk JSON: status item baru, status pengajuan, nilai produk, dan stale.

    Contoh:
        {"item": {"id": 15, "correction_id": 7, "field_name": "fiber_100g", ...,
                  "status": "approved", "status_label": "Disetujui", "review_note": ""},
         "correction": {"id": 7, "status": "partial", "status_label": "Sebagian disetujui"},
         "product": {"id": 6, "field_name": "fiber_100g", "value": 2.5},
         "stale": false}
    """
    item = result.item
    correction = item.correction
    product = correction.product  # query baru: nilai sesudah ditinjau
    return {
        "item": {"id": item.pk, "correction_id": item.correction_id, **serialize_item(item)},
        "correction": {
            "id": correction.pk,
            "status": correction.status,
            "status_label": correction.get_status_display(),
        },
        "product": {
            "id": product.pk,
            "field_name": item.field_name,
            "value": to_column_value(item.field_name, get_current_value(product, item.field_name)),
        },
        "stale": result.stale,
    }


def _queue_return_url(request):
    """Alamat kembali sesudah meninjau: input next dari form, tetapi HANYA alamat antrean
    /moderasi/ di situs ini (mencegah open redirect). Selain itu kembali ke /moderasi/.

    Contoh:
        next="/moderasi/?tab=semua&page=2"  -> "/moderasi/?tab=semua&page=2"
        next="https://contoh.com/"          -> "/moderasi/"
    """
    queue_url = reverse("data_correction:queue")
    target = request.POST.get("next", "")
    safe = url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return target if safe and target.startswith(queue_url) else queue_url


def _review_message(result):
    """Pesan toast sesudah meninjau (satu pesan saja: toast hanya menampilkan yang terakhir).

    Contoh:
        "Serat (g/100 g) untuk Sarimi isi 2 Goreng Ayam Kremes disetujui; data produk sudah diperbarui."
        "Merek untuk Sarimi isi 2 Goreng Ayam Kremes ditolak; catatan tersimpan untuk pengaju."
    """
    item = result.item
    subject = f"{item.get_field_name_display()} untuk {item.correction.product.product_name or 'produk'}"
    if item.status != APPROVED:
        return f"{subject} ditolak; catatan tersimpan untuk pengaju."
    message = f"{subject} disetujui; data produk sudah diperbarui."
    if result.stale:
        message += " Nilai produk sempat berubah sejak diajukan dan kini sudah ditimpa."
    return message


@staff_required
@require_POST
@_json_404("correction_not_found", "Item tidak ditemukan atau pengajuannya sudah ditarik.")
def review_item(request, pk):
    """Setujui atau tolak SATU item koreksi (PRD F-4.4). Khusus is_staff.

    POST action=approve|reject dan review_note (wajib saat menolak, opsional saat menyetujui).
    - HTML : kembali ke antrean (input next, hanya alamat /moderasi/) dengan pesan toast.
             Kalau gagal, panel item yang sama dibuka lagi bersama pesan errornya.
    - JSON : 200 {"item", "correction", "product", "stale"}; item yang sudah ditinjau 409.

    Contoh:
        POST /moderasi/item/15/tinjau/?format=json  action=approve
            -> 200 {"item": {..., "status": "approved"}, "product": {"value": 2.5, ...}, ...}
        POST yang sama sekali lagi
            -> 409 {"error": {"id": "already_reviewed", "message": "Item ini sudah ditinjau."}}
    """
    item = get_object_or_404(DataCorrectionItem, pk=pk)
    back_url = _queue_return_url(request)
    form = ReviewForm(request.POST)
    try:
        if not form.is_valid():
            first_error = next(iter(form.errors.values()))[0]
            raise services.CorrectionError("validation_error", first_error, fields=form.errors)
        note = form.cleaned_data["review_note"]
        if form.cleaned_data["action"] == APPROVE:
            result = services.approve_item(request.user, item, note)
        else:
            result = services.reject_item(request.user, item, note)
    except services.CorrectionError as error:
        if wants_json(request):
            return json_error(error.message, error.fields, error.status, error.error_id)
        messages.error(request, error.message)
        return redirect(f"{back_url}{'&' if '?' in back_url else '?'}item={item.pk}")
    if wants_json(request):
        return json_ok(serialize_review(result))
    messages.success(request, _review_message(result))
    return redirect(back_url)