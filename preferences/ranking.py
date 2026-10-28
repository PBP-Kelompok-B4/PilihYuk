"""Pengurutan data yang sudah dimuat pemanggil; tidak melakukan query database."""

from .constants import NUTRIENT_FIELDS


def order_metric_rows(preferences, default_rows):
    """Dahulukan preferensi berbobot besar; seri mengikuti urutan bawaan."""
    weights = {item.nutrient: item.weight for item in preferences if item.nutrient in NUTRIENT_FIELDS}
    rows = list(default_rows)
    preferred = [key for key in rows if key in weights]
    preferred.sort(key=lambda key: -weights[key])
    remaining = [key for key in rows if key in NUTRIENT_FIELDS and key not in weights]
    unknown = [key for key in rows if key not in NUTRIENT_FIELDS]
    return preferred + remaining + unknown


def rank_products(products, preferences):
    """Jumlahkan skor min-max berbobot; produk tanpa data berada di akhir."""
    products = list(products)
    scores = [0.0] * len(products)
    known = [False] * len(products)
    for preference in preferences:
        if preference.nutrient not in NUTRIENT_FIELDS:
            continue
        field = NUTRIENT_FIELDS[preference.nutrient]["field"]
        values = [getattr(product, field, None) for product in products]
        available = [value for value in values if value is not None]
        if not available:
            continue
        low, high = min(available), max(available)
        for index, value in enumerate(values):
            if value is None:
                continue
            known[index] = True
            # Nilai sama memberi kontribusi setara; data kosong tidak mendapat skor.
            if low == high:
                normalized = 1.0
            else:
                normalized = (value - low) / (high - low)
                if preference.direction == "min":
                    normalized = 1 - normalized
            scores[index] += preference.weight * normalized
    ordered = sorted(range(len(products)), key=lambda index: (not known[index], -scores[index]))
    return [products[index] for index in ordered]
