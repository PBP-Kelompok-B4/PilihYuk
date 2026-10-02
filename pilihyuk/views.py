from django.shortcuts import render

# ponytail: data contoh dari wireframe Landing. Ganti dengan query Product dan Shelf saat modelnya ada.
SAMPLE_PRODUCTS = [
    {"name": "Indomie Mi Goreng", "brand": "Indomie · 85 g", "nutri": "B", "green": "C", "estimated": False,
     "nova": 4, "kcal": 447, "protein": 9, "sugar": 7, "sodium": 900},
    {"name": "Mie Sedaap Goreng", "brand": "Mie Sedaap · 91 g", "nutri": "C", "green": "B", "estimated": False,
     "nova": 4, "kcal": 450, "protein": 8, "sugar": 8, "sodium": 850},
    {"name": "Sarimi Isi 2 Goreng", "brand": "Sarimi · 88 g", "nutri": "C", "green": None, "estimated": False,
     "nova": 4, "kcal": 452, "protein": 7.5, "sugar": 6.5, "sodium": 870},
    {"name": "Supermi Goreng", "brand": "Supermi · 80 g", "nutri": "B", "green": "C", "estimated": True,
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
# (path ikon di static, judul, keterangan)
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
# (label, key, satuan, arah terbaik: "max", "min", atau None bila tidak dinilai)
METRICS = [
    ("Kalori", "kcal", "kcal", None),
    ("Protein", "protein", "g", "max"),
    ("Gula", "sugar", "g", "min"),
    ("Natrium", "sodium", "mg", "min"),
]


def comparison_rows():
    """Satu baris per metrik: nilai tiap produk, lebar bar (% dari terbesar), dan penanda nilai terbaik."""
    rows = []
    for label, key, unit, best in METRICS:
        values = [p[key] for p in SAMPLE_PRODUCTS]
        target = {"max": max, "min": min}.get(best, lambda _: None)(values)
        cells = [{"value": v, "pct": round(100 * v / max(values)), "best": v == target} for v in values]
        rows.append({"label": label, "unit": unit, "best": best, "cells": cells})
    return rows


def home_page(request):
    return render(request, "index.html", {
        "products": SAMPLE_PRODUCTS,
        "rows": comparison_rows(),
        "shelves": SAMPLE_SHELVES,
        "steps": STEPS,
        "benefits": BENEFITS,
    })
