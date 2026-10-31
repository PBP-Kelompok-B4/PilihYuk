# Evaluasi SDK Open Food Facts

Diuji 2 Oktober 2026. SDK Python (`openfoodfacts` 5.3.0) dijalankan. SDK Dart (3.30.2) hanya dibaca kodenya karena belum ada toolchain Flutter.

## Keputusan

| Kebutuhan | Pilihan | Alasan |
|-----------|---------|--------|
| Seeding | Saring dump CSV dengan Python stdlib, simpan sebagai fixture | SDK hanya bisa mengunduh dump penuh dan tidak punya pembungkus search v2 |
| Lookup barcode dan refresh | Klien `requests` tipis di `product_catalog/open_food_facts.py` | SDK tidak menolak produk non-Indonesia, mengubah 404 jadi `None`, dan tidak retry 503 HTML |
| Flutter di PAS | Hanya memanggil endpoint JSON Django | Koreksi lokal, produk manual, skor estimasi, filter Indonesia, dan normalisasi nilai kosong ada di Django |

Tidak ada dependency baru, karena `requests` sudah ada di `requirements.txt`.

## SDK Dart di PAS

Tidak dipakai untuk memanggil OFF langsung. Yang masih berguna: validasi barcode di sisi klien sebelum memanggil Django, dan rujukan nama field. SDK tidak punya pemindai kamera, jadi pemindai butuh paket terpisah. Jangan memakai `saveProduct` atau fungsi tulis lain, karena proyek ini tidak mengirim koreksi ke OFF.

## Kontrak JSON Django

Supaya PAS tidak memaksa perubahan model:

| Hal | Aturan |
|-----|--------|
| Nama field | Nama kolom Django (`product_name`, `nutrition_grade`, `energy_kcal_100g`, dan seterusnya), bukan nama OFF |
| Grade | Selalu string: `a` sampai `e` (lingkungan juga `a-plus` dan `f`), `"unknown"`, `"not-applicable"`. Tidak pernah `null` |
| Angka | `nova_group` dan kolom gizi bernilai `null` bila kosong. `0` berarti nol yang sah |
| Barcode | Selalu string hasil normalisasi, `null` untuk produk manual tanpa barcode |
| Estimasi | `environmental_grade` (resmi) terpisah dari `environmental_grade_estimated`, ditambah boolean `environmental_is_estimated` |
| Sumber | `source` dan `last_synced_at` (ISO 8601), serta `off_url` untuk produk `source=off` |
| Paginasi | `{"count", "page", "page_size", "results"}` |
| Error | `{"error": {"id": "...", "message": "..."}}` dengan kode HTTP yang sesuai |
