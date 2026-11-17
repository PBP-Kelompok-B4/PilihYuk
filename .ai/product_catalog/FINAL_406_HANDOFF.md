# Seed catalog: 406 reviewed products

Replaces the earlier 6,591 and 6,594 seed scopes. Seeding is limited to the reviewed manifest. Runtime lookup follows its own, separate rules (see the last section).

## Dataset and admission

- `seed/off_seed_dataset.json` lists exactly 406 canonical unique barcodes plus the 62 approved seed-only overrides. `seed/off_seed_exclusions.json` keeps all 889 exclusions unchanged. Both live in the `product_catalog/seed/` package (31 October), next to `off_mapping.py`, `name_eligibility.py`, `seed_dataset.py`, `seed_exclusions.py` and `fixture_data.py`.
- CSV and fixture commands load both files and fail closed if either is malformed. They admit only manifest members that have an official Nutri-Score `a` to `e` and valid name and model fields. Country evidence is the exact tag `en:indonesia`, and barcode normalization and grade precedence are the existing ones. Manual products and local corrections face no score gate.
- Source: the 8,186-row Indonesian subset of the OFF CSV dump. The 437 country and grade matches, minus 30 without a name and 1 with an invalid barcode, give 406. Rows are not selected from active database rows.
- Versioned fixture: `fixtures/products-406.json`, with a source-hash sidecar. `seed_products` loads it by default. The older `fixtures/products.json` and `seed/fixture_data.py` are the small research fixture (20 products) and are not the final dataset. Do not regenerate it to build the final one.

## Seeding

Each local SQLite database is separate. After migrating your own database:

```
python manage.py seed_products
python manage.py seed_products
```

A fresh database gets 406 products, and the second run creates none. Existing manual barcodes and locally edited or inactive rows are preserved. Seeding never changes the active state of existing rows. Do not use `loaddata` on a populated database, because it overwrites rows with the same `pk`.

From the reviewed CSV (not in the repo):

```
python manage.py seed_products --csv PATH_TO_FINAL_CSV --dry-run
python manage.py seed_products --csv PATH_TO_FINAL_CSV
python manage.py build_off_fixture --csv PATH_TO_FINAL_CSV --output PATH_TO_NEW_FIXTURE.json
```

The exporter's default limit is 406. A dry run on all 8,186 rows accepts exactly 406 with no errors. `manual_review=62` is the first name screen's flag count, and those 62 identities are now approved.

## Local synchronization (done 11 October 2026)

`sync_reviewed_catalog` aligned the local database with the reviewed 406: 62 products activated and 6,250 outside the manifest deactivated, none deleted (7,647 stored, 406 active OFF, 7,241 inactive). It changes only `is_active` and `updated_at`, and verifies the rest against a backup. It also checks SQLite integrity and foreign keys, tests a no-op repeat, and refuses unrecognized drift. A repeat changed zero rows. Manual, user, and history data were untouched. Product ID 45 (Pringles Original 107gr, `8886467100017`) has source grade `e` but a stored grade of `unknown`, and sync keeps that local value.

## Tests

Seeding and sync checks passed: fixture membership, grades, CSV parity, all 62 overrides, rejection of non-members and wrong countries, repeated import, manual ownership, `ProductView` and corrections, atomic rollback, and repeat sync. The real-CSV integration test runs with `PILIHYUK_FINAL_CSV=PATH_TO_FINAL_CSV python manage.py test product_catalog`. Test counts for the whole project are in the root README.

## Runtime boundary

Runtime code, timeouts, quota, JSON, and AJAX are unchanged. Runtime still accepts unknown scores and still rejects all 889 excluded barcodes, including the 62 allowed for seeding. A seeded product can therefore appear in the catalog while barcode lookup rejects it, and runtime can import products outside the manifest. A regression test pins this boundary. It needs a separate team decision, so the catalog is not a closed 406-only set. Decision 16 (four of six rows) and K-12 and K-13 in the PRD remain unresolved.
