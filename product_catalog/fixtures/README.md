## Local 406 synchronization completed with explicit approval

Executed 11 October 2026 at 15:48 UTC: 62 OFF products activated, 6,250 OFF
products outside the final manifest deactivated, zero deleted. Local counts:
7,647 stored / 406 active OFF / 7,241 inactive. Manual/user/history data and
all non-status product fields remain unchanged; Pringles ID 45 stays unknown.
Backup restore, foreign keys, integrity and actual repeat sync passed; repeat
changed zero rows/timestamps and produced identical CSV. Runtime policy remains
separate and unchanged. Earlier pending-approval/database counts below are
historical. Evidence: `%LOCALAPPDATA%/Temp/pilihyuk-final-406-sbwefpbc/`
`post-sync-integrity.json` and `after-sync-active-verification.json`.

## Current decision: 406 seed members; 62 seed-only exceptions approved

The user approved the 62 overlapping codes for CSV/fixtures only. Final seeding
now uses the 406-member manifest and known source Nutri-Scores. Runtime remains
unchanged with all 889 exclusions and no score gate. Persistent synchronization
is prepared/tested but not applied; local database still has 6,594 active rows.
See [current handoff, files and sync plan](../FINAL_406_HANDOFF.md). Earlier decisions/results
below are retained as historical evidence and are superseded where conflicting.

## Runtime policy approved and aligned (11 October 2026)

User approved runtime without a Nutri-Score requirement, with the same name
screening and 889 barcode exclusions as CSV/fixtures. Local OFF lookup no longer
rejects eligible unknown-score products. Manual products remain exempt. Excluded
requested barcodes fail before quota reservation/network, and a missing/malformed
exclusion list fails closed. Exact Indonesia, GTIN validation, model checks,
10-second timeout, finite retries, JSON errors and per-user quota are preserved.
Invalid nutrition grades map to unknown; environmental-score validation remains
strict. Earlier text below describing pending runtime decisions is historical
and superseded by this approval. No persistent status changes are authorized.

## Current final-dataset policy (11 October 2026)

CSV exporter and fixture loader now enforce the reviewed 889 exclusions and
non-food/unusable name rules without a known Nutri-Score requirement. Model
validation remains mandatory. The old 50-record fixture below is historical;
use build_off_fixture --limit 6591 with the final reviewed CSV for team handoff.
Never bypass country provenance with an arbitrary fixture or use loaddata on a
populated database. See ../README.md for current commands. Earlier score gates
and 39-product counts below are historical, superseded for fixture paths.

# OFF development fixture and CSV pipeline

Current OFF admission requires exact en:indonesia plus Nutri-Score a–e.
The historical file still has 50 records; seed_products now admits its 39
known-score entries and does not overwrite existing products. CSV fixture exports
also filter unknown/invalid scores. See [current policy and cleanup](../CSV_SEEDING.md).
The earlier 50-product setup evidence below is historical, not a current guarantee.

`products.json` contains 50 real food/drink records from the committed research
sample `.claude/pilihyuk-docs/off-samples/q1_v2_search_sample.json`. The findings
document dates that API v2 search sample to 2 October 2026. This is a historical,
popularity-biased sample, not a fresh API fetch or a full CSV import.
Every selected record is checked for the exact `en:indonesia` countries tag when
building the fixture. `fixture_data.CODES` identifies all 50 source records.
This confirms the saved OFF availability claim, not current retail availability.

From the repository root, with the project environment configured:

```powershell
python -m product_catalog.fixture_data
python manage.py seed_products
```

The first command deterministically rebuilds the JSON from the saved sample;
it never accesses the network. The second loads it atomically, allocates local
primary keys, and skips existing barcodes (including inactive/manual records).
Repeated loads preserve existing edits, ownership, IDs, relationships and status.
This supplies the PRD's minimum 50 seedable products, without asserting that
any deployment has already loaded them. Each member's SQLite database is separate.
It does not create a shared team database or prove deployment availability.
Use this loader on populated databases, rather than `loaddata`, which overwrites
matching fixture primary keys. Standard `loaddata products` is only appropriate
for an empty disposable database. Review the diff before regenerating the fixture.

Mapping is in `off_mapping.py`: Indonesian name first, then default/English;
environmental_score_grade before ecoscore_grade, falling back for missing values;
known grade values remain separate from estimated grades. Unknown/not-applicable
markers are preserved if no known fallback exists. Nutrient zeroes survive;
unavailable/nonfinite numbers become null; sodium stays in grams in storage.
Empty lists are [], and halal_labeled means only presence of en:halal.
Category uses the last supplied category tag with a small Indonesian translation
dictionary and readable source-name fallback; tag order is not a specificity claim.
Origin comes only from origins_tags/manufacturing_places, never countries_tags.
All original category/label tags are retained, including contradictory source tags.
Missing ingredients/allergens/serving sizes in this selected-field sample are left
empty, not inferred. No environmental estimates are calculated.

Fixture timestamps are the fixed build date, not OFF modification timestamps.
The loader uses actual insertion timestamps. last_synced_at remains null because
these records have not been synchronized by the application with the live API.

Source: [Open Food Facts](https://openfoodfacts.org).
Database structure: ODbL; individual contents: DbCL; product images: CC BY-SA,
as documented in PRD section 5/NF-10. Images remain external OFF URLs. Preserve
this attribution and the shared footer when redistributing or demonstrating data.

## Local CSV/gzip export (no database writes)

```powershell
.venv/Scripts/python.exe manage.py build_off_fixture --csv PATH_TO_DUMP.csv.gz --output products-from-csv.json --limit 200
```

The exporter streams the tab-separated dump, keeps exact Indonesian sale tags,
maps fields with the same helper, validates Product without uniqueness queries,
skips invalid/duplicate records and codes over 14 digits, and writes a fixture
plus `products-from-csv.json.provenance.json` (source SHA-256 and selection rule).
It never downloads data, calls OFF, or inserts database records. Use the same
dump bytes/options and mapper revision for reproducibility. Review the output.

Decision 16 (minimum four of six comparison rows) and K-12/K-13 remain open.
No completeness threshold or API enrichment is silently applied. The committed
50-product fixture is still from the historical search snapshot, not a full CSV
population. Missing detail fields stay empty; current retail availability is not
verified. Full CSV execution and counters are recorded in
[CSV_SEEDING.md](../CSV_SEEDING.md).

After migration, members may run `seed_products --fixture products-from-csv.json`
themselves. Only use fixtures produced/reviewed through an Indonesia-validating
builder: countries_tags is not a Product column, so the loader cannot independently
reconstruct the original sale-country claim. It validates model/source/barcodes,
loads atomically, and rolls back if a record fails. Do not use `loaddata` on a
populated database. Full local CSV database execution is documented separately in
[CSV_SEEDING.md](../CSV_SEEDING.md).
