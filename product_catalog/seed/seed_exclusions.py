"""Reviewed barcode exclusions, applied automatically to OFF CSV seeding."""
import json
from pathlib import Path

from ..open_food_facts import normalize_barcode

EXCLUSIONS_FILE = Path(__file__).with_name("off_seed_exclusions.json")


def load_seed_exclusions():
    """Fail closed if the reviewed list is absent or malformed; no optional flag."""
    data = json.loads(EXCLUSIONS_FILE.read_text(encoding="utf-8"))
    codes = data["canonical_barcodes"]
    if (not isinstance(codes, list) or len(codes) != 889 or data.get("count") != 889
            or any(not isinstance(code, str) or not code.isascii() or not code.isdigit()
                   or len(code) > 14 or normalize_barcode(code) != code for code in codes)
            or len(set(codes)) != len(codes)):
        raise ValueError("Reviewed OFF seed exclusions must contain 889 unique canonical barcodes")
    return frozenset(codes)
