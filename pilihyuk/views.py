from django.shortcuts import render
from django.urls import reverse

from product_catalog.models import Product

# featured_shelf() memakai Product; featured_shelves() masih contoh sampai integrasi Shelf.
# Kunci produk: name, brand (merek dan ukuran), nutri ("a" sampai "e", atau None), green (huruf atau None),
# estimated, nova, kcal, protein, sugar, sodium (None bila kosong), image dan url (opsional).
# Kunci shelf: title, context, count, desc, user, thumbs (3 url atau None), url.
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
        target = {"max": max, "min": min}.get(best, lambda _: None)(known) if len(known) >= 2 else None
        largest = max(known, default=0)
        cells = [{"value": v, "pct": round(100 * v / largest) if v is not None and largest else 0,
                  "best": v is not None and v == target} for v in values]
        rows.append({"label": label, "unit": unit, "best": best, "cells": cells})
    return rows


def featured_shelf():
    """Contoh maksimal empat produk aktif; bukan shelf milik pengguna."""
    products = []
    for product in Product.objects.filter(is_active=True).order_by("product_name", "pk")[:4]:
        nutri = product.nutrition_grade.strip().lower()
        green = product.environmental_grade.strip().lower()
        estimate = product.environmental_grade_estimated.strip()
        nutri = nutri if nutri in {"a", "b", "c", "d", "e"} else None
        green = green if green in {"a-plus", "a", "b", "c", "d", "e", "f"} else None
        if estimate.lower() in {"", "unknown", "not-applicable"}:
            estimate = None
        products.append({
            "name": product.product_name or "Produk tanpa nama",
            "brand": " · ".join(value for value in (product.brand, product.quantity) if value),
            "nutri": nutri,
            "green": green or estimate,
            "estimated": green is None and estimate is not None,
            "nova": product.nova_group,
            "kcal": product.energy_kcal_100g,
            "protein": product.proteins_100g,
            "sugar": product.sugars_100g,
            "sodium": product.sodium_100g * 1000 if product.sodium_100g is not None else None,
            "image": product.image_url,
            "url": reverse("product_catalog:product_detail", args=[product.pk]),
        })
    return {"title": "Contoh produk dari katalog", "count": len(products),
            "sort": "Nama produk", "products": products}


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
