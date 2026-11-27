# API Modul 4: Antrean Data

Prefix `/api/v1/corrections/`. Kode: `data_correction/api_views.py`, `serializers.py`, `permissions.py`. Aturan tetap di `services.py`, `moderation.py`, `validators.py`, dan `contribution.py`, sama dengan web. Contoh diambil dari data tes.

## Autentikasi

- Masuk lewat `POST /api/v1/auth/login/`; sesi tersimpan di `CookieRequest`.
- GET memakai `request.get(url)`. POST, PATCH, dan DELETE memakai `sendJson(request, 'PATCH', url, data)` dari `lib/api.dart` (mengirim `X-CSRFToken` dan `Referer`).
- `request.get` tidak memberi status code. Balasan sukses tidak pernah punya kunci `detail` atau `code`, jadi kunci itu menandai galat.

## Galat

```json
{"detail": "Periksa kembali isian koreksi.", "code": "validation_error", "fields": {"nova_group": ["Grup NOVA harus bilangan bulat 1 sampai 4."]}}
```

| Status | `code` | Kapan |
|--------|--------|-------|
| 400 | `validation_error` | Isian salah, `items` kosong, status tinjau asing, menolak tanpa catatan |
| 403 | `authentication_required` | Belum masuk atau sesi kedaluwarsa |
| 403 | `forbidden` | Pengguna biasa di endpoint kurator |
| 404 | `product_not_found` | Produk tidak ada atau nonaktif |
| 404 | `correction_not_found` | Pengajuan tidak ada atau milik orang lain; item tidak ada atau sudah ditarik |
| 409 | `product_inactive`, `already_reviewed`, `not_withdrawable`, `not_editable` | Setujui atau ubah usulan untuk produk nonaktif; item sudah ditinjau; tarik atau ubah pengajuan yang sudah ditinjau |
| 403, 400, 405 | tanpa `code` | Galat DRF: CSRF gagal, body bukan JSON, metode tidak didaftarkan |

## Endpoint

| Metode | URL | Siapa | Query atau body | Sukses |
|--------|-----|-------|-----------------|--------|
| GET | `me/` | publik | | `{"logged_in": true, "is_staff": false}` |
| GET | `queue/` | publik | `?sort=shelf\|kosong\|terbaru&missing=&page=` | halaman antrean, 20 per halaman |
| GET | `products/<pk>/form/` | masuk | `?field=` (boleh berulang) | `product`, `focus`, `correctable_fields` (14) |
| GET | `mine/` | masuk | `?page=` | halaman pengajuan, 10 per halaman, terbaru dulu |
| POST | `mine/` | masuk | `{"product": 1, "items": [{"field_name": "sodium_100g", "proposed_value": "500"}]}` | 201, satu pengajuan |
| GET | `mine/<pk>/` | pemilik | | satu pengajuan |
| PATCH | `mine/<pk>/` | pemilik | `{"items": [{"field_name": "sodium_100g", "proposed_value": "500"}]}` | 200, satu pengajuan, selama semua item Menunggu |
| DELETE | `mine/<pk>/` | pemilik | | 204 tanpa body, selama semua item Menunggu |
| GET | `moderation/` | kurator | `?tab=antrean\|semua&field=&status=&page=` | halaman baris item, 20 per halaman |
| GET | `moderation/guide/` | kurator | | `{"fields": [{"field_name", "label", "kind", "rules"}]}` |
| GET | `moderation/items/<pk>/` | kurator | | satu baris item |
| PATCH | `moderation/items/<pk>/` | kurator | `{"status": "approved"\|"rejected", "review_note": "..."}` | hasil tinjau |

- Tab `antrean` hanya berisi item Menunggu, terlama dulu. Tab `semua` berisi semua status, terbaru dulu, dan `?status=` hanya berlaku di sini. `?tab=panduan` dan nilai asing kembali ke bawaan.
- `review_note` wajib saat menolak.
- **PATCH `mine/<pk>/`** (bonus, hanya di aplikasi):
  - `items` adalah daftar lengkap yang baru. Field boleh ditambah atau dihapus, minimal satu, dan aturan isiannya sama dengan POST.
  - Produk tidak bisa diganti; `product` di body diabaikan.
  - Item lama diganti item baru (id baru, `old_value` dari nilai produk saat itu), jadi kurator yang masih membuka item lama mendapat 404.
  - Begitu ada item yang ditinjau: 409 `not_editable`.
- `?page=` yang bukan angka menjadi 1; yang melewati batas menjadi halaman terakhir.

## Bentuk JSON

```
halaman      : count, page, page_size, num_pages, next_page, previous_page, results
               + queue/      : sort, missing, shelf_available, sort_options, missing_options, stats
               + moderation/ : tab, field, status, tab_options, field_options, status_options,
                               stats {pending, approved, rejected}
product      : id, product_name, brand, quantity, image_url, is_active
pengajuan    : id, product, status, status_label, is_withdrawable, created_at, items[]
item         : id, field_name, label, old_value, proposed_value, old_display, proposed_display,
               status, status_label, review_note
baris item   : id, correction_id, product, submitted_by, created_at, field_name, label,
               old/proposed/current _value dan _display, status, status_label, review_note, stale
field form   : field_name, label, group, type (text|integer|number), current_value, current_display,
               display_factor, help_text
hasil tinjau : item (baris item), correction {id, status, status_label},
               product {id, field_name, value, display}, stale, message
```

- **Status pengajuan** diturunkan dari item:
  - `pending` (Menunggu)
  - `approved` (Disetujui)
  - `rejected` (Ditolak)
  - `partial` (Sebagian disetujui)
- **`is_withdrawable`** true hanya bila semua item masih Menunggu.
- **`submitted_by`** hanya nama tampilan.
- **`stale` di baris item** true bila item masih Menunggu dan nilai produk sudah berubah sejak diajukan.
- **`stale` di hasil tinjau** memberi tahu bahwa nilai itu sempat berubah sebelum disetujui.

Contoh item (natrium):

```json
{"id": 2, "field_name": "sodium_100g", "label": "Natrium (mg/100 g)", "old_value": 0.78, "proposed_value": 0.5,
 "old_display": "780", "proposed_display": "500", "status": "pending", "status_label": "Menunggu", "review_note": ""}
```

## Satuan

- `*_value`: satuan kolom `Product` (natrium dalam gram, NOVA bilangan bulat); `null` berarti tidak diketahui.
- `*_display`: teks siap tampil (koma desimal, natrium dalam mg); `null` berarti "Tidak diketahui".
- Saat mengajukan, `proposed_value` dikirim apa adanya dari kotak isian (natrium dalam mg). `display_factor` bernilai 1000 untuk natrium dan 1 untuk field lain.

## Cara mencoba

- **Browsable API:**
  1. Jalankan `.\env\Scripts\python.exe manage.py runserver`.
  2. Masuk di `http://127.0.0.1:8000/masuk/`.
  3. Buka `/api/v1/corrections/...`. POST dan PATCH lewat "Raw data" (`application/json`); DELETE lewat tombol merah.
- **Emulator:** server yang sama, lalu di folder mobile jalankan `flutter run --dart-define=BASE_URL=http://10.0.2.2:8000`.
- **Tes:** `tests_api_submit`, `tests_api_mine`, `tests_api_update`, `tests_api_moderation`, `tests_api_access`, `tests_api_flow`.
