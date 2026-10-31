from preferences.constants import NUTRIENT_FIELDS
from product_catalog.seed.off_mapping import tag_name

MAX_COMPARED = 4
NUTRI_ORDER = ["a", "b", "c", "d", "e"]
GREEN_ORDER = ["a-plus", "a", "b", "c", "d", "e", "f"]
NUTRIENTS = [
    ("Energi", "energy_kcal_100g", "kkal", None),
    ("Protein", "proteins_100g", "g", "max"),
    ("Lemak", "fat_100g", "g", None),
    ("Lemak jenuh", "saturated_fat_100g", "g", "min"),
    ("Karbohidrat", "carbohydrates_100g", "g", None),
    ("Gula", "sugars_100g", "g", "min"),
    ("Serat", "fiber_100g", "g", "max"),
    ("Natrium", "sodium_100g", "mg", "min"),
]


def mark_best(cells, direction):
    ranks = [cell["rank"] for cell in cells if cell["rank"] is not None]
    if not direction or len(ranks) < 2 or len(set(ranks)) == 1:
        return
    target = max(ranks) if direction == "max" else min(ranks)
    for cell in cells:
        cell["best"] = cell["rank"] == target


def row(label, kind, values, ranks, direction=None, unit="", field=None):
    cells = [{"value": value, "rank": rank, "best": False} for value, rank in zip(values, ranks)]
    mark_best(cells, direction)
    return {"label": label, "kind": kind, "unit": unit, "direction": direction, "field": field, "cells": cells}


def grade_row(label, kind, values, order):
    return row(label, kind, values, [order.index(v) if v in order else None for v in values], "min")


def comparison_rows(products, preferences=()):
    chosen = {NUTRIENT_FIELDS[p.nutrient]["field"]: p for p in preferences if p.nutrient in NUTRIENT_FIELDS}
    green = grade_row("Green-Score", "green", [p.environmental_grade for p in products], GREEN_ORDER)
    for cell, product in zip(green["cells"], products):
        cell["estimate"] = product.environmental_grade_estimated if cell["rank"] is None else ""
    rows = [
        grade_row("Nutri-Score", "nutri", [p.nutrition_grade for p in products], NUTRI_ORDER),
        green,
        row("NOVA", "nova", [p.nova_group for p in products], [p.nova_group for p in products], "min",
            field="nova_group"),
    ]
    nutrients = []
    for label, field, unit, direction in NUTRIENTS:
        preference = chosen.get(field)
        values = [getattr(p, field) for p in products]
        if field == "sodium_100g":
            values = [None if v is None else round(v * 1000, 1) for v in values]
        top = max((v for v in values if v is not None), default=0)
        nutrient = row(label, "number", values, values, preference.direction if preference else direction, unit, field)
        nutrient["preferred"] = preference is not None
        for cell in nutrient["cells"]:
            cell["pct"] = round(100 * cell["value"] / top) if cell["value"] and top else 0
        nutrients.append((nutrient, preference))
    nutrients.sort(key=lambda pair: -pair[1].weight if pair[1] else 0)
    rows += [nutrient for nutrient, _ in nutrients]
    rows.append(row("Kemasan", "text", [", ".join(tag_name(t) for t in p.packaging_tags) for p in products],
                    [None] * len(products)))
    rows.append(row("Asal", "text", [p.origin for p in products], [None] * len(products), field="origin"))
    for line in rows:
        for cell, product in zip(line["cells"], products):
            cell["product_id"] = product.pk
    return rows
