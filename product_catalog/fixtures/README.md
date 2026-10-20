# Small OFF development fixture

`products.json` contains 20 real food/drink records from the committed research
sample `.claude/pilihyuk-docs/off-samples/q1_v2_search_sample.json`. The findings
document dates that API v2 search sample to 2 October 2026. This is a historical,
popularity-biased sample, not a fresh API fetch or the planned 196-product CSV seed.
Every selected record is checked for the exact `en:indonesia` countries tag when
building the fixture. `fixture_data.CODES` identifies all 20 source records.
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
It is a small fixture loader; full CSV population remains a later task.
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
