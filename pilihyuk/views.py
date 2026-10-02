from django.shortcuts import render

# data contoh dari wireframe. Tukar featured_shelf() dan featured_shelves() dengan query Product dan Shelf.
# Kunci produk: name, brand (merek dan ukuran), nutri ("a" sampai "e", atau None), green (huruf atau None),
# estimated, nova, kcal, protein, sugar, sodium (None bila kosong), image dan url (opsional).
# Kunci shelf: title, context, count, desc, user, thumbs (3 url atau None), url.
SAMPLE_PRODUCTS = [
    {"name": "Indomie Mi Goreng", "brand": "Indomie · 85 g", "nutri": "b", "green": "C", "estimated": False,
     "nova": 4, "kcal": 447, "protein": 9, "sugar": 7, "sodium": 900},
    {"name": "Mie Sedaap Goreng", "brand": "Mie Sedaap · 91 g", "nutri": "c", "green": "B", "estimated": False,
     "nova": 4, "kcal": 450, "protein": 8, "sugar": 8, "sodium": 850},
    {"name": "Sarimi Isi 2 Goreng", "brand": "Sarimi · 88 g", "nutri": "c", "green": None, "estimated": False,
     "nova": 4, "kcal": 452, "protein": 7.5, "sugar": 6.5, "sodium": 870},
    {"name": "Supermi Goreng", "brand": "Supermi · 80 g", "nutri": "b", "green": "C", "estimated": True,
     "nova": 4, "kcal": 440, "protein": 8.5, "sugar": 6, "sodium": 780},
]
SAMPLE_SHELVES = [
    {"context": "Alfamart", "count": 12, "title": "Mie instan goreng di minimarket",
     "desc": "Pilihan mie instan goreng yang biasa ditemukan di minimarket.", "user": "rani_a"},
    {"context": "Dapur", "count": 8, "title": "Yang bisa dituang ke kopi",
     "desc": "Krimer, susu, dan oat milk untuk kopi pagi di kos.", "user": "bagas"},
    {"context": "Kampus", "count": 9, "title": "Camilan tinggi protein",
     "desc": "Camilan yang bisa dibawa ke kelas atau kantor.", "user": "dinda"},
    {"context": "Minimarket", "count": 11, "title": "Minuman rendah gula",
     "desc": "Teh, soda, dan air kemasan dengan gula lebih rendah.", "user": "farel"},
]
STEPS = [
    ("img/search-2.svg", "Cari produk", "Telusuri produk makanan dan minuman dari katalog Open Food Facts."),
    ("img/layers-2.svg", "Buat atau pilih shelf", "Susun kumpulan produk yang benar-benar saling menggantikan."),
    ("img/columns-3.svg", "Bandingkan", "Lihat gizi, skor, dan dampak lingkungan berdampingan dalam satu tabel."),
    ("img/bookmark-check.svg", "Pilih", "Simpan keputusan beserta alasannya ke riwayat pribadimu."),
]
BENEFITS = [
    ("img/layers-3.svg", "Perbandingan berbasis shelf",
     "Produk dibandingkan dengan alternatif nyata dalam satu keputusan pembelian, bukan per kategori."),
    ("img/sliders-horizontal.svg", "Preferensi nutrisi dua arah",
     "Maksimalkan protein, batasi gula, atau atur bobotnya. Tabel mengikuti preferensimu."),
    ("img/repeat.svg", "Substitusi dari komunitas", "Usulan penggantian dari pengguna lain lengkap dengan alasan dan voting."),
    ("img/shield-check.svg", "Transparansi data", "Nilai resmi, estimasi, dan data yang belum tersedia selalu dibedakan."),
]
METRICS = [
    ("Kalori", "kcal", "kcal", None),
    ("Protein", "protein", "g", "max"),
    ("Gula", "sugar", "g", "min"),
    ("Natrium", "sodium", "mg", "min"),
]


def comparison_rows(products):
    """Satu baris per metrik: nilai tiap produk, lebar bar (% dari terbesar), dan penanda nilai terbaik.
    Nilai None (data kosong) tidak ikut diperingkat."""
    rows = []
    for label, key, unit, best in METRICS:
        values = [p[key] for p in products]
        known = [v for v in values if v is not None]
        target = {"max": max, "min": min}.get(best, lambda _: None)(known) if known else None
        cells = [{"value": v, "pct": round(100 * v / max(known)) if v and max(known) else 0,
                  "best": v is not None and v == target} for v in values]
        rows.append({"label": label, "unit": unit, "best": best, "cells": cells})
    return rows


def featured_shelf():
    """Shelf untuk tabel contoh: kunci shelf ditambah 'public', 'sort', dan 'products' (maksimal 4)."""
    return {"title": "Mie instan goreng di minimarket", "count": 12, "public": True, "sort": "Protein ↑",
            "products": SAMPLE_PRODUCTS}


def featured_shelves():
    return [{"thumbs": [None] * 3, "url": "/shelf/", **s} for s in SAMPLE_SHELVES]


def home_page(request):
    shelf = featured_shelf()
    return render(request, "index.html", {
        "shelf": shelf,
        "rows": comparison_rows(shelf["products"]),
        "shelves": featured_shelves(),
        "steps": STEPS,
        "benefits": BENEFITS,
    })
