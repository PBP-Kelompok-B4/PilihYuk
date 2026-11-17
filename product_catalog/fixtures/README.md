# Small OFF development fixture

`products.json` holds 20 real food and drink records built from the saved research sample `.ai/product_catalog/helpers/off-samples/q1_v2_search_sample.json` (an API v2 search from 2 October 2026, so historical and biased toward popular products, not a fresh fetch). Each record is checked for the exact `en:indonesia` countries tag, and `seed/fixture_data.py` (`CODES`) lists the 20 source records. This confirms OFF's saved availability claim, not current retail availability. The final 406-product dataset is described in `.ai/product_catalog/FINAL_406_HANDOFF.md`.

From the repository root:

```
python -m product_catalog.seed.fixture_data
python manage.py seed_products
```

The first command rebuilds the JSON deterministically from the saved sample and never touches the network. The second loads it atomically with local primary keys and skips existing barcodes (including inactive and manual ones), so repeated loads keep edits, ownership, IDs, relationships and status. Use it on populated databases instead of `loaddata`, which overwrites rows with matching primary keys. Review the diff before regenerating the fixture.

## Mapping (`seed/off_mapping.py`)

- Name: Indonesian first, then default, then English.
- Environmental grade: `environmental_score_grade` before `ecoscore_grade`. Known grades stay separate from estimated grades, and unknown or not-applicable markers are kept when no known fallback exists.
- Numbers: nutrient zeroes survive, unavailable or non-finite values become null, and sodium stays in grams.
- Lists: empty ones are `[]`. `halal_labeled` means only that `en:halal` is present.
- Category: the last supplied category tag, through a small Indonesian dictionary, with the readable source name as fallback. Tag order does not claim specificity. All original category and label tags are kept, including contradictory ones.
- Origin: only from `origins_tags` and `manufacturing_places`, never `countries_tags`.
- Missing ingredients, allergens and serving sizes stay empty, and no environmental estimates are calculated.
- Fixture timestamps are the fixed build date, not OFF modification times. `last_synced_at` stays null because the application has not synced these records with the live API.

## Attribution

Source: [Open Food Facts](https://openfoodfacts.org). Database structure: ODbL, contents: DbCL, product images: CC BY-SA (PRD section 5, NF-10). Images remain external OFF URLs. Keep this attribution and the shared footer when redistributing or demonstrating the data.
