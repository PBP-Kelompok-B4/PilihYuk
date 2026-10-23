"""Final seed membership; deliberately independent of runtime admission."""
import json
from pathlib import Path

from .open_food_facts import normalize_barcode
from .seed_exclusions import load_seed_exclusions

MANIFEST = Path(__file__).with_name("off_seed_dataset.json")
FINAL_FIXTURE = Path(__file__).with_name("fixtures") / "products-406.json"


def load_seed_dataset():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    codes = data["canonical_barcodes"]
    overrides = data["seed_only_exclusion_overrides"]
    excluded = load_seed_exclusions()
    if (data.get("count") != 406 or data.get("source_country_tag") != "en:indonesia"
            or not isinstance(codes, list) or len(codes) != len(set(codes)) or len(codes) != 406
            or any(not isinstance(c, str) or not c.isascii() or not c.isdigit()
                   or len(c) > 14 or normalize_barcode(c) != c for c in codes)
            or not isinstance(overrides, list) or len(overrides) != len(set(overrides))
            or len(overrides) != 62 or set(overrides) != set(codes) & excluded):
        raise ValueError("Invalid reviewed 406 seed manifest or 62 seed-only exceptions")
    return data


def is_seed_member(code, codes):
    return code in codes
