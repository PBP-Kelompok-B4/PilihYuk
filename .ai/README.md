# Dokumen tim PilihYuk

Dokumen kerja bersama ini ikut di-commit. Cara menjalankan proyek ada di [`../README.md`](../README.md). ERD ada di tautan Drive pada README proyek.

## Proyek

| Berkas | Isi |
|--------|-----|
| `PRD.md` | Kebutuhan, model data, risiko, dan semua keputusan (bagian 13) |
| `timeline.md` | Tenggat, status branch, pembagian modul, aturan kerja, dan sisa tugas |
| `HANDOFF.md` | Kondisi proyek dan butir terbuka (bahasa Inggris) |
| `first-brief.md` | Arsip rapat 4 Oktober |

## Per modul

| Folder | Isi |
|--------|-----|
| `product_catalog/` (Modul 1) | `off-api-findings.md` (uji API Open Food Facts), `off-sdk-evaluation.md` (alasan memakai klien `requests` tipis dan kontrak JSON untuk Flutter), `FINAL_406_HANDOFF.md` (seed 406 produk) |
| `product_catalog/helpers/` | `off-samples/` (respons mentah API yang dirujuk `off-api-findings.md`) dan `tools/check_off_encodings.py` (skrip riset OFF, `--selftest` menjalankan tesnya) |
| `preferences/` (Modul 5) | `NOTES.md` (kontrak endpoint dan perilaku) |
| `accounts/` (Auth) | `reset-password-plan.md` |

Modul 2, 3, dan 4 belum punya dokumen khusus. Taruh dokumennya di folder bernama sama dengan app-nya.

`product_catalog/helpers/off-samples/q1_v2_search_sample.json` dibaca juga oleh `product_catalog/seed/fixture_data.py`. Kalau dipindah, ubah path di berkas itu.
