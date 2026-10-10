"""Check how Open Food Facts encodes missing values for Indonesian products.

Answers four open questions about OFF data quality:
  1. Coverage of Nutri-Score and environmental score.
  2. Every distinct value in the grade fields (decides Django `choices`).
  3. How missing nutrients are encoded inside `nutriments`.
  4. Coverage of `origins_tags` / `manufacturing_places`.

Standard library only. Run it on your own machine (needs internet):

    python3 check_off_encodings.py                  # 1 v2 search + 20 v3 lookups
    python3 check_off_encodings.py --v3-sample 50   # more v3 lookups
    python3 check_off_encodings.py --dump openfoodfacts-products.jsonl.gz --limit 500
    python3 check_off_encodings.py --csv en.openfoodfacts.org.products.csv.gz --limit 0   # all Indonesian rows
    python3 check_off_encodings.py --selftest        # asserts for normalize_barcode / is_indonesian

The API sample is biased toward popular, better-documented products, so real
coverage across the whole Indonesian catalog is likely lower than reported.
The --dump mode avoids that bias but needs the multi-GB nightly dump.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from typing import Any, Iterable, Iterator

USER_AGENT = (
    "PilihYuk/0.1 (PBP Fasilkom UI; https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/; "
    "https://github.com/pbp-Kelompok-B4/PilihYuk/)"
)
BASE = "https://id.openfoodfacts.org"

GRADE_FIELDS = ["nutrition_grades", "ecoscore_grade", "environmental_score_grade"]
NUTRIENT_KEYS = [
    "energy-kcal_100g",
    "proteins_100g",
    "fat_100g",
    "saturated-fat_100g",
    "sugars_100g",
    "fiber_100g",
    "salt_100g",
    "carbohydrates_100g",  # added after the Figma wireframe review
    "sodium_100g",
]
FIELDS = [
    "code",
    "product_name",
    "nutrition_grades",
    "ecoscore_grade",
    "environmental_score_grade",
    "nova_group",
    "origins_tags",
    "manufacturing_places",
    "countries_tags",
    "nutriments",
    "misc_tags",
]
MISSING_MARKERS = {"unknown", "not-applicable", ""}

# Official per-IP limits (https://openfoodfacts.github.io/openfoodfacts-server/api/):
# 10 req/min for search, 15 req/min for product reads. Pauses stay below that.
V2_PAUSE_S = 7.0
V3_PAUSE_S = 4.5


HTTP_STATS: Counter = Counter()  # status code -> count, printed at the end (evidence for Q8)
RETRY_BACKOFF_S = (15, 30, 60)    # OFF answers 503 intermittently (HTML body, not JSON)


def http_get_json(url: str) -> dict[str, Any]:
    """GET with retry on 429/503. Raises HTTPError after the last retry."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(len(RETRY_BACKOFF_S) + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                HTTP_STATS[resp.status] += 1
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            HTTP_STATS[exc.code] += 1
            if exc.code not in (429, 503) or attempt == len(RETRY_BACKOFF_S):
                raise
            wait = RETRY_BACKOFF_S[attempt]
            print(f"  HTTP {exc.code}, retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise AssertionError("unreachable")


def fetch_v2_search(page_size: int) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "countries_tags_en": "indonesia",
            "fields": ",".join(FIELDS),
            "page_size": page_size,
        }
    )
    data = http_get_json(f"{BASE}/api/v2/search?{params}")
    return data.get("products", [])


def fetch_v3_product(code: str) -> dict[str, Any] | None:
    params = urllib.parse.urlencode({"fields": ",".join(FIELDS)})
    try:
        data = http_get_json(f"{BASE}/api/v3/product/{urllib.parse.quote(code)}?{params}")
    except urllib.error.HTTPError as exc:
        print(f"  v3 {code}: HTTP {exc.code}", file=sys.stderr)
        return None
    return data.get("product")


def iter_dump(path: str, limit: int) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.endswith(".gz") else open
    found = 0
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            try:
                product = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not is_indonesian(product):
                continue
            yield {k: product.get(k) for k in FIELDS if k in product}
            found += 1
            if found >= limit:
                return


CSV_LIST_COLS = ["origins_tags", "countries_tags", "labels_tags", "packaging_tags", "categories_tags",
                 "ingredients_analysis_tags", "states_tags"]


def iter_csv(path: str, limit: int) -> Iterator[dict[str, Any]]:
    """Stream the OFF CSV export (tab separated, gzip) and yield Indonesian products.

    Shaped like API products so `report()` works unchanged. Empty cells become absent keys.
    The CSV has `environmental_score_grade` (not `ecoscore_grade`), no `misc_tags`
    and no `product_name_id`. limit <= 0 means no limit.
    """
    opener = gzip.open if path.endswith(".gz") else open
    found = 0
    with opener(path, "rt", encoding="utf-8", newline="") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        width = len(header)
        for line in fh:
            if INDONESIA_TAG not in line:  # cheap pre-filter before splitting
                continue
            cells = line.rstrip("\n").split("\t")
            if len(cells) != width:
                continue
            row = {k: v for k, v in zip(header, cells) if v != ""}
            for col in CSV_LIST_COLS:
                if col in row:
                    row[col] = row[col].split(",")
            if not is_indonesian(row):
                continue
            if "nutriscore_grade" in row:
                row["nutrition_grades"] = row["nutriscore_grade"]
            if _is_number(row.get("nova_group")):
                row["nova_group"] = int(float(row["nova_group"]))
            row["nutriments"] = {k: float(v) for k, v in row.items() if k.endswith("_100g") and _is_number(v)}
            yield row
            found += 1
            if 0 < limit <= found:
                return


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def classify(container: dict[str, Any], key: str) -> str:
    """Describe how one value is encoded: absent, null, a string, or a number."""
    if key not in container:
        return "absent"
    value = container[key]
    if value is None:
        return "null"
    if isinstance(value, bool):
        return f"bool:{value}"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return f"string:{value!r}"
    if isinstance(value, list):
        return "empty-list" if not value else "list"
    return type(value).__name__


def is_known(product: dict[str, Any], key: str) -> bool:
    value = product.get(key)
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in MISSING_MARKERS
    if isinstance(value, list):
        return len(value) > 0
    return True


def _is_valid_upc12(code: str) -> bool:
    """12 digits with a valid UPC-A check digit (Products.pm is_valid_upc12)."""
    if len(code) != 12 or not code.isdigit():
        return False
    digits = [int(c) for c in code]
    odd = sum(digits[0:11:2])
    even = sum(digits[1:11:2])
    return (10 - (odd * 3 + even) % 10) % 10 == digits[11]


def normalize_barcode(raw: str | None) -> str | None:
    """Mirror OFF's `normalize_code` (openfoodfacts-server lib/ProductOpener/Products.pm:470-514, :580-606).

    Keep digits only; a valid UPC-12 gets one leading 0; a 14-digit code starting
    with 0 loses it; then leading zeros are stripped and the code is padded to 13
    digits; a 13-digit result starting with 00000 becomes an 8-digit EAN-8.
    ponytail: GS1 data strings / GS1 digital links are not parsed (server does).
    """
    if raw is None:
        return None
    code = "".join(c for c in str(raw) if c.isdigit())
    if _is_valid_upc12(code):
        code = "0" + code
    if len(code) == 14 and code[0] == "0":
        code = code[1:]
    if not code:
        return code
    code = code.lstrip("0")
    if len(code) < 13:
        code = code.rjust(13, "0")
    if len(code) == 13 and code.startswith("00000"):
        code = code[5:]
    return code


INDONESIA_TAG = "en:indonesia"


def is_indonesian(product: dict[str, Any] | None) -> bool:
    """True when the product is *sold* in Indonesia (`countries_tags`), not made there.

    One rule for seeding, barcode lookup and refresh. Same check works on dump rows,
    v2 search items and v3 `product` objects. Missing or malformed field -> False.
    """
    if not isinstance(product, dict):
        return False
    tags = product.get("countries_tags")
    return isinstance(tags, list) and INDONESIA_TAG in tags


def selftest() -> None:
    # Observed live: 12-digit UPC -> 13 digits.
    assert normalize_barcode("089686010947") == "0089686010947"
    assert normalize_barcode("0089686010947") == "0089686010947"
    # Observed live: 0000000000017 resolves to EAN-8 00000017.
    assert normalize_barcode("0000000000017") == "00000017"
    assert normalize_barcode("17") == "00000017"
    # 8 digits stay 8 digits, 7 digits pad to 8 (documented rule).
    assert normalize_barcode("96385074") == "96385074"
    assert normalize_barcode("0000096385074") == "96385074"
    # 9-12 digits pad to 13 (documented: 034000470693 -> 0034000470693).
    assert normalize_barcode("034000470693") == "0034000470693"
    assert normalize_barcode("123456789") == "0000123456789"
    # 13 digits unchanged; 14 digits starting with 0 lose it; other 14 digits stay.
    assert normalize_barcode("3017620422003") == "3017620422003"
    assert normalize_barcode("03017620422003") == "3017620422003"
    assert normalize_barcode("13017620422000") == "13017620422000"
    # Non-digits are dropped; empty/None are passed through.
    assert normalize_barcode(" 3017-6204 22003 ") == "3017620422003"
    assert normalize_barcode(None) is None
    assert normalize_barcode("") == ""
    assert normalize_barcode("abc") == ""

    assert is_indonesian({"countries_tags": ["en:france", "en:indonesia"]})
    assert not is_indonesian({"countries_tags": ["en:france"]})
    assert not is_indonesian({"countries_tags": []})
    assert not is_indonesian({"countries_tags": None})
    assert not is_indonesian({"countries_tags": "en:indonesia"})  # string, not list
    assert not is_indonesian({})
    assert not is_indonesian(None)
    print("selftest ok")


def pct(part: int, whole: int) -> str:
    return f"{part}/{whole} ({100 * part / whole:.0f}%)" if whole else "0/0"


def report(label: str, products: list[dict[str, Any]]) -> None:
    n = len(products)
    print(f"\n=== {label}: {n} products ===")
    if n == 0:
        print("No products returned.")
        return

    print("\n[2] Distinct encodings per grade field")
    for field in GRADE_FIELDS + ["nova_group"]:
        counts = Counter(classify(p, field) for p in products)
        print(f"  {field}:")
        for enc, c in counts.most_common():
            print(f"    {enc:<40} {c}")

    print("\n[1] Coverage (value present and not unknown / not-applicable)")
    for field in ["nutrition_grades", "ecoscore_grade", "environmental_score_grade", "nova_group"]:
        print(f"  {field:<28} {pct(sum(is_known(p, field) for p in products), n)}")
    either_env = sum(
        is_known(p, "ecoscore_grade") or is_known(p, "environmental_score_grade") for p in products
    )
    print(f"  {'any environmental grade':<28} {pct(either_env, n)}")

    print("\n[3] How each nutrient is encoded inside `nutriments`")
    no_nutriments = sum(1 for p in products if not isinstance(p.get("nutriments"), dict))
    if no_nutriments:
        print(f"  products without a `nutriments` object: {no_nutriments}")
    for key in NUTRIENT_KEYS:
        counts = Counter(
            classify(p["nutriments"], key)
            for p in products
            if isinstance(p.get("nutriments"), dict)
        )
        summary = ", ".join(f"{enc}={c}" for enc, c in counts.most_common())
        print(f"  {key:<20} {summary}")

    print("\n[4] Origin coverage")
    for field in ["origins_tags", "manufacturing_places"]:
        print(f"  {field:<22} {pct(sum(is_known(p, field) for p in products), n)}")
    either_origin = sum(
        is_known(p, "origins_tags") or is_known(p, "manufacturing_places") for p in products
    )
    print(f"  {'either':<22} {pct(either_origin, n)}")

    print("\n[extra] Most common completeness-related misc_tags")
    tags = Counter(
        t
        for p in products
        for t in (p.get("misc_tags") or [])
        if any(s in t for s in ("missing", "not-computed", "not-applicable", "estimated"))
    )
    for tag, c in tags.most_common(12):
        print(f"  {tag:<60} {c}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--page-size", type=int, default=100, help="v2 search sample size")
    parser.add_argument("--v3-sample", type=int, default=20, help="how many barcodes to re-read via v3")
    parser.add_argument("--dump", help="path to openfoodfacts-products.jsonl(.gz); skips the API")
    parser.add_argument("--limit", type=int, default=500, help="Indonesian products to read from the dump")
    parser.add_argument("--csv", help="path to en.openfoodfacts.org.products.csv(.gz); skips the API (limit 0 = all rows)")
    parser.add_argument("--selftest", action="store_true", help="run assert tests for normalize_barcode/is_indonesian and exit")
    args = parser.parse_args(argv)

    if args.selftest:
        selftest()
        return 0

    if args.dump:
        report(f"Dump {args.dump}", list(iter_dump(args.dump, args.limit)))
        return 0

    if args.csv:
        report(f"CSV {args.csv}", list(iter_csv(args.csv, args.limit)))
        return 0

    try:
        v2 = fetch_v2_search(args.page_size)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"v2 search failed: {exc}. If HTTP 503, wait a minute and retry.", file=sys.stderr)
        return 1
    report("API v2 search", v2)

    codes = [p["code"] for p in v2 if p.get("code")][: args.v3_sample]
    v3: list[dict[str, Any]] = []
    time.sleep(V2_PAUSE_S)
    for code in codes:
        product = fetch_v3_product(code)
        if product is not None:
            v3.append(product)
        time.sleep(V3_PAUSE_S)
    report("API v3 product (same barcodes)", v3)
    print(f"\nHTTP status counts (incl. retries): {dict(HTTP_STATS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())