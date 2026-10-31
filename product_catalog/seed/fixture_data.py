"""Rebuild the development fixture from the committed OFF research snapshot.

Run from the repository root: python -m product_catalog.seed.fixture_data
No HTTP requests or database writes are performed.
"""

import json
from pathlib import Path

from .off_mapping import product_fields


ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = ROOT / ".ai/product_catalog/helpers/off-samples/q1_v2_search_sample.json"
FIXTURE = Path(__file__).resolve().parent.parent / "fixtures/products.json"
# Explicit selection preserves reproducibility even if the sample order changes.
CODES = (
    "80053835", "0089686120714", "3451790188718", "8906010500870",
    "3451790019142", "8904071704527", "8992760221028", "8901058005080",
    "5010477346032", "3451790019159", "3451790188831", "0089686170726",
    "3451790011917", "8997240600041", "8996001600269", "3451790011856",
    "3451790886256", "3451790019166", "8852756346053", "8996001600146",
    '0753950000254',
    '8904071701090',
    '0089686010947',
    '8990044000048',
    '3451790397868',
    '8998009010613',
    '8994963002824',
    '0089686170795',
    '3451790019135',
    '8997240600010',
    '8992760121014',
    '8886008101091',
    '8996001440124',
    '8886008101053',
    '3451790397622',
    '8997035563414',
    '8997009510123',
    '5010775204959',
    '8998866632287',
    '8996001440049',
    '3451790019685',
    '3451790019678',
    '8992770094117',
    '8997240602854',
    '8886467100017',
    '8998866200301',
    '8000500220412',
    '8990044000000',
    '8996001301142',
    '8886467100055',
)


def build_fixture():
    records = {record["code"]: record for record in json.loads(SOURCE.read_text(encoding="utf-8"))["products"]}
    fixture = []
    for pk, code in enumerate(CODES, start=1):
        fields = product_fields(records[code])
        fields.update({
            "is_active": True, "added_by": None, "last_synced_at": None,
            # Fixed fixture-build date, not the source's modification/sync time.
            "created_at": "2026-10-10T00:00:00Z", "updated_at": "2026-10-10T00:00:00Z",
        })
        fixture.append({"model": "product_catalog.product", "pk": pk, "fields": fields})
    return fixture


if __name__ == "__main__":
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(build_fixture(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(CODES)} products to {FIXTURE}")
