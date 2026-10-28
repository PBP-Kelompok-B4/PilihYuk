"""Responses helper HTML/JSON untuk view Modul 4 (NF-3).

Notes:
- Alat bantu kecil agar setiap view bisa membalas dalam DUA bentuk,
  yaitu HTML untuk browser dan JSON untuk aplikasi Flutter nanti (NF-3), plus decorator
  untuk membatasi akses (wajib login, khusus kurator).
- Kenapa tidak memakai product_catalog/responses.py langsung? Aturan tetap melarang
  mengimpor fungsi internal app lain. Jadi file ini MENIRU bentuknya, supaya Flutter
  menerima bentuk JSON yang sama dari semua modul.
- Aturan bentuk JSON (sama dengan katalog):
  - permintaan dianggap JSON kalau ada ?format=json atau header Accept berisi
    application/json;
  - objek dikirim langsung, tanpa pembungkus;
  - daftar memakai {"count", "page", "page_size", "results"};
  - error berbentuk {"error": {"id", "message"}}, ditambah "fields" untuk kesalahan
    isian. "fields" memakai bentuk form.errors.get_json_data():
        {"brand": [{"message": "...", "code": "..."}]}
- Aturan akses:
  - permintaan HTML TIDAK PERNAH dibalas JSON;
  - pengunjung yang belum masuk: JSON 401, atau HTML dialihkan ke halaman masuk
    (LOGIN_URL) dengan ?next= agar kembali ke halaman semula setelah login;
  - pengguna biasa di halaman kurator: 403.
- Id error yang dipakai modul ini:
      validation_error       400   isian tidak valid
      authentication_required 401  belum masuk
      forbidden              403   bukan kurator
      product_not_found      404   produk tidak ada
      correction_not_found   404   pengajuan tidak ada / milik orang lain / sudah ditarik
      product_inactive       409   produk nonaktif
      already_reviewed       409   item sudah ditinjau
      not_withdrawable       409   pengajuan sudah mulai ditinjau

Daftar fungsi publik:
- wants_json, json_ok, json_error, field_errors, page_payload, render_or_json
- decorator: login_required_json, staff_required
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render


def wants_json(request):
    """True kalau klien meminta JSON.

    Contoh:
        GET /antrean/?format=json                    -> True
        header Accept "application/json"             -> True
        header Accept "text/html,application/xhtml+xml" -> False (browser biasa)
    """
    return request.GET.get("format") == "json" or "application/json" in request.headers.get("Accept", "")


def json_ok(data, status=200):
    """Balasan sukses: objek dikirim langsung, tanpa pembungkus.

    Contoh:
        json_ok({"id": 3, "status": "pending"}, status=201)
            -> HTTP 201, body {"id": 3, "status": "pending"}
    """
    return JsonResponse(data, status=status)


def json_error(message, errors=None, status=400, error_id="validation_error"):
    """Balasan error dengan bentuk yang sama seperti katalog.

    Argumen:
        message  : kalimat untuk pengguna
        errors   : opsional, pesan per field (dict biasa atau form.errors)
        status   : kode HTTP (bawaan 400)
        error_id : kode singkat error (bawaan "validation_error")

    Contoh:
        json_error("Periksa kembali isian koreksi.", {"nova_group": ["Grup NOVA ..."]})
            -> HTTP 400, body {"error": {"id": "validation_error", "message": "Periksa ..."},
                               "fields": {"nova_group": [{"message": "Grup NOVA ...", "code": "invalid"}]}}
        json_error("Item ini sudah ditinjau.", status=409, error_id="already_reviewed")
            -> HTTP 409, body {"error": {"id": "already_reviewed", "message": "Item ini sudah ditinjau."}}
    """
    body = {"error": {"id": error_id, "message": message}}
    if errors:
        body["fields"] = field_errors(errors)
    return JsonResponse(body, status=status)


def field_errors(errors):
    """Samakan bentuk pesan per field dengan form.errors.get_json_data().

    Menerima tiga bentuk masukan:
        - form.errors (ErrorDict dari form Django)
        - dict biasa {field: [pesan, ...]}
        - dict biasa {field: pesan}

    Contoh:
        {"brand": ["Isian ini wajib diisi."]}
            -> {"brand": [{"message": "Isian ini wajib diisi.", "code": "invalid"}]}
    """
    # form.errors sudah punya method sendiri untuk bentuk JSON.
    if hasattr(errors, "get_json_data"):
        return errors.get_json_data()
    # Dict biasa (mis. CorrectionError.fields dari services.py): ubah ke bentuk yang sama.
    result = {}
    for field, messages in errors.items():
        if not isinstance(messages, (list, tuple)):
            messages = [messages]  # satu pesan -> daftar berisi satu pesan
        result[str(field)] = [
            message if isinstance(message, dict) else {"message": str(message), "code": "invalid"}
            for message in messages
        ]
    return result


def page_payload(page, results):
    """Bungkus daftar berpaginasi, sama dengan katalog.

    Argumen:
        page    : objek Page dari Django Paginator
        results : isi halaman itu, sudah dalam bentuk dict siap JSON

    Contoh:
        (halaman 2 dari Paginator(..., 12), [{...}, {...}])
            -> {"count": 30, "page": 2, "page_size": 12, "results": [{...}, {...}]}
    """
    return {
        "count": page.paginator.count,      # total semua data, bukan hanya halaman ini
        "page": page.number,                # nomor halaman saat ini
        "page_size": page.paginator.per_page,
        "results": list(results),
    }


def render_or_json(request, template_name, context, data, status=200):
    """Satu view, dua bentuk balasan: JSON kalau diminta, selain itu render template.

    Argumen:
        template_name : template HTML, mis. "data_correction/queue.html"
        context       : data untuk template HTML
        data          : data untuk JSON. Boleh berupa fungsi tanpa argumen (mis. lambda),
                        supaya data JSON hanya disusun kalau memang diminta.

    Contoh:
        render_or_json(request, "data_correction/queue.html", {"rows": rows},
                       lambda: page_payload(page, rows))
            -> dengan ?format=json : JSON daftar berpaginasi
            -> tanpa               : halaman HTML queue.html
    """
    if wants_json(request):
        return json_ok(data() if callable(data) else data, status=status)
    return render(request, template_name, context, status=status)


def login_required_json(view):
    """Wajib masuk. Pengganti @login_required bawaan Django yang juga mengerti JSON.

    - Pengunjung + JSON  -> 401 authentication_required
    - Pengunjung + HTML  -> redirect ke LOGIN_URL?next=<halaman semula>
    - Sudah masuk        -> view dijalankan seperti biasa

    Contoh (pengunjung):
        GET /antrean/saya/              -> 302 ke /masuk/?next=/antrean/saya/
        GET /antrean/saya/?format=json  -> 401 {"error": {"id": "authentication_required", ...}}
    """
    @wraps(view)  # menjaga nama dan docstring view asli
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if wants_json(request):
                return json_error(
                    "Silakan masuk terlebih dahulu.", status=401, error_id="authentication_required"
                )
            return redirect_to_login(request.get_full_path())
        return view(request, *args, **kwargs)

    return wrapped


def staff_required(view):
    """Khusus kurator (is_staff).

    - Pengunjung            -> diperlakukan seperti login_required_json (401 / redirect)
    - Pengguna biasa + JSON -> 403 forbidden
    - Pengguna biasa + HTML -> 403 (PermissionDenied, menampilkan halaman 403 Django)
    - Kurator               -> view dijalankan seperti biasa

    Contoh (pengguna biasa):
        GET /moderasi/              -> 403
        GET /moderasi/?format=json  -> 403 {"error": {"id": "forbidden", ...}}
    """
    @wraps(view)
    @login_required_json
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            if wants_json(request):
                return json_error("Halaman ini khusus kurator.", status=403, error_id="forbidden")
            raise PermissionDenied("Halaman ini khusus kurator.")
        return view(request, *args, **kwargs)

    return wrapped