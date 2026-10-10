"""Pure OFF-to-Product field mapping; no model imports or database writes."""

from .open_food_facts import has_value, is_number, is_sold_in_indonesia, normalize_barcode


NUTRIENT_KEYS = {
    "energy_kcal_100g": "energy-kcal_100g",
    "proteins_100g": "proteins_100g",
    "fat_100g": "fat_100g",
    "saturated_fat_100g": "saturated-fat_100g",
    "carbohydrates_100g": "carbohydrates_100g",
    "sugars_100g": "sugars_100g",
    "fiber_100g": "fiber_100g",
    "sodium_100g": "sodium_100g",
}

# Small display dictionary; all original tags remain available on Product.
CATEGORY_NAMES = {
    "en:instant-noodles": "Mi instan",
    "en:waters": "Air minum",
    "en:mineral-waters": "Air mineral",
    "en:oat-milks": "Susu oat",
    "en:potato-crisps": "Keripik kentang",
    "en:biscuits": "Biskuit",
}


def tag_name(tag):
    return tag.partition(":")[2].replace("-", " ") if ":" in tag else tag.replace("-", " ")


def text_value(record, *keys):
    for key in keys:
        if has_value(record, key) and isinstance(record[key], str):
            return record[key].strip()
    return ""


def list_value(record, key):
    value = record.get(key)
    return [tag for tag in value if isinstance(tag, str) and tag.strip()] if isinstance(value, list) else []


def official_grade(record, primary, fallback):
    """Prefer a known primary grade, then fallback; preserve missing markers."""
    value = text_value(record, primary, fallback)
    if value:
        return value
    for key in (primary, fallback):
        if record.get(key) in ("unknown", "not-applicable"):
            return record[key]
    return "unknown"


def product_fields(record):
    """Map a confirmed Indonesian record; leave synchronization/ownership to callers.

    Category selection is a local display convention: the last supplied tag,
    translated where known, otherwise its readable source name. This does not
    assert that OFF guarantees tag ordering or taxonomy specificity.
    """
    if not is_sold_in_indonesia(record):
        raise ValueError("OFF product is not confirmed as sold in Indonesia")
    code = normalize_barcode(record.get("code"))
    if not code or len(code) > 14:
        raise ValueError("OFF product needs a barcode of at most 14 digits")
    categories = list_value(record, "categories_tags")
    origins = list_value(record, "origins_tags")
    labels = list_value(record, "labels_tags")
    nova = record.get("nova_group")
    nutrients = record.get("nutriments")
    nutrients = nutrients if isinstance(nutrients, dict) else {}
    fields = {
        "code": code,
        "product_name": text_value(record, "product_name_id", "product_name", "product_name_en"),
        "brand": text_value(record, "brands"),
        "quantity": text_value(record, "quantity"),
        "image_url": text_value(record, "image_url"),
        "category": CATEGORY_NAMES.get(categories[-1], tag_name(categories[-1])) if categories else "",
        "origin": ", ".join(map(tag_name, origins)) or text_value(record, "manufacturing_places"),
        "nutrition_grade": official_grade(record, "nutriscore_grade", "nutrition_grades"),
        "environmental_grade": official_grade(record, "environmental_score_grade", "ecoscore_grade"),
        "environmental_grade_estimated": "",
        "nova_group": int(float(nova)) if is_number(nova) and float(nova) in (1, 2, 3, 4) else None,
        "halal_labeled": "en:halal" in labels,
        "ingredients_text": text_value(record, "ingredients_text_id", "ingredients_text"),
        "allergens": list_value(record, "allergens_tags"),
        "serving_size": text_value(record, "serving_size"),
        "categories_tags": categories,
        "labels_tags": labels,
        "source": "off",
    }
    for key in ("packaging_tags", "ingredients_analysis_tags", "misc_tags"):
        fields[key] = list_value(record, key)
    for field, key in NUTRIENT_KEYS.items():
        value = nutrients.get(key)
        fields[field] = float(value) if is_number(value) else None
    return fields
