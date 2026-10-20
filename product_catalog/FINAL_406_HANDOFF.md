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

# Final seed dataset: 406 reviewed products

This supersedes the historical 6,591/6,594 seed scope and the initial 406
exclusion blocker. The user approved the 62 overlapping barcode exceptions for
CSV seeding/fixtures only. Runtime remains separately governed.

## Dataset and admission

`off_seed_dataset.json` records exactly 406 canonical unique barcodes and the
62 approved seed-only overrides. `off_seed_exclusions.json` remains unchanged
with all 889 entries. CSV/fixture commands load both, fail closed if malformed,
and admit only manifest members with valid official nutrition grades a-e and
valid names/model fields. CSV uses exact `en:indonesia` and existing normalization,
grade precedence and barcode rules. Runtime GTIN validation is unchanged.
No score gate is imposed on manual products or existing local corrections.

Exact source: the complete 8,186-row `indonesia-all.csv` subset and its provenance,
plus historical `nutriscore-dry-global.json`: 437 country/grade matches minus
30 missing names and 1 invalid barcode = 406. No selection from active DB rows.
Source subset SHA-256:
`a4abd80f3073a869fbb4770a5f2fc73f383a65fda18c9b8fb1fd42fe66323761`.

Final CSV and reports directory:
`C:/Users/Yasmin/AppData/Local/Temp/pilihyuk-final-406-sbwefpbc/`.
CSV: `eligible-products-406.csv`, SHA-256:
`d12f9aba7bc10f3a6a58902df31d9ee7f8e93dee954e47087e07a1aca8400588`.
406 rows, 406 unique canonical codes, exact country evidence and grades a-e for
all 406; zero overlap with the effective seed exclusions after the 62 approvals.
`verification.json`, `seed-dry-run.json`, `sync-dry-run.json`, and
`sync-rehearsal-verification.json` record actual checks.

The versioned final fixture is `fixtures/products-406.json`, with its source
hash sidecar. CSV and fixture contain the same 406 products and mapped values.
`seed_products` now defaults to this fixture; the old `fixtures/products.json`
and `fixture_data.py` research builder remain historical evidence, not the final
handoff. Do not regenerate the old research fixture to build the final dataset.

## Member setup and rebuilding

Each local SQLite database is separate. No shared database is provided. After
members configure their own environment and migrate their own new local DB:

```powershell
.venv/Scripts/python.exe manage.py seed_products
.venv/Scripts/python.exe manage.py seed_products
```

Fresh database: 406 created; second run: zero created, existing fields/statuses
unchanged. Existing manual barcode collisions and locally edited/inactive rows
are preserved. Seeding does not synchronize existing active states.

Equivalent CSV route (use the verified final file above):

```powershell
.venv/Scripts/python.exe manage.py seed_products --csv PATH_TO_FINAL_CSV --dry-run
.venv/Scripts/python.exe manage.py seed_products --csv PATH_TO_FINAL_CSV
.venv/Scripts/python.exe manage.py build_off_fixture --csv PATH_TO_FINAL_CSV --output PATH_TO_NEW_FIXTURE.json
```

The exporter default limit is 406. Keep source/audit evidence before replacing
an existing generated artifact. Fixture loaders accept approved members only;
country evidence comes from the reviewed manifest/source provenance because
Product has no countries_tags field. Do not load unreviewed arbitrary fixtures
with loaddata into populated databases.

The real local dry-run accepted all 406, all already stored, zero errors and
zero would-create/updates. `manual_review=62` is the conservative name screen's
original flag count; these identities have now been explicitly approved, not
awaiting another name review. Missing or invalid source grades are rejected.

## Local synchronization awaiting approval

Persistent database is still 7,647 stored / 6,594 active / 1,053 inactive.
The user approved seed exceptions, not execution of this status reconciliation.
Actual command dry-run: activate 62, deactivate 6,250, delete 0; target 406 active
OFF plus unchanged active manual products (currently manual total/active = 0).
`sync-dry-run.json` lists exact activation/deactivation IDs. Historical IDs
1/Classico, 24/Pocky and 32/AQUA are outside the manifest and will be inactive;
their records and relations remain. No historical exception is retained.

`sync_reviewed_catalog` now pins the reviewed 406 CSV and current pre-sync
backup/hash. The previous 6,594 configuration is preserved in audit evidence.
The command restores/verifies the backup, uses BEGIN EXCLUSIVE, validates all
changed models, updates only is_active/updated_at, verifies every other field
and table against backup, checks SQLite integrity/FKs, tests a no-op repeat,
and validates staged CSV before commit. It refuses unrecognized snapshot drift.
The report's excluded_active refers to effective seed exclusions; the 62
runtime exclusions remain in force, as stated separately in that report.

Backup: `%LOCALAPPDATA%/Temp/pilihyuk-406-audit-m6gvz8xa/pre-406-sync.sqlite3`.
Report: same directory, `backup-verification.json`. Old and fresh backups were
restored successfully; all 18 tables/schema matched, integrity=ok, FK errors=0.
Fresh backup SHA-256:
`b9627feab14369d9eefcb38521a5a172c6d1ff70b1b3b4dfa0cefbc2401291b5`.
Application DB SHA-256 remains:
`dc435dcae3e79e59cbad9c2ab534076c80ea669593b741b70d4bfffa2615bf20`.

Dry-run command (omit --apply until separate approval):

```powershell
.venv/Scripts/python.exe manage.py sync_reviewed_catalog --csv PATH_TO_FINAL_CSV --backup PATH_TO_PRE_406_BACKUP --backup-report PATH_TO_BACKUP_VERIFICATION --output PATH_OUTSIDE_REPO/active-406.csv
```

Actual apply/repeat was rehearsed only on a disposable copy of the full local
database: first 62 activated/6,250 deactivated, 406 active, all other data
preserved; repeat zero changes and byte-identical export. Deliberate snapshot
drift was rejected. This is not a claim that the application DB was synchronized.

ID 45, Pringles Original 107gr (`8886467100017`), has source grade e but stored
grade unknown. Sync preserves that local value; 406 known source grades do not
imply 406 known stored grades. Refreshing any local value needs a separate decision.

## Tests and unresolved runtime/integration scope

Completed validation for this implementation:

| Check | Actual result |
|---|---|
| Changed CSV/fixture tests + real CSV integration | PASS, 50 tests |
| New manifest/runtime-boundary/sync regressions | PASS, 9 tests |
| Full product_catalog suite, actual 406 CSV enabled | PASS, 163 tests, 16.741s |
| Full project suite, actual 406 CSV enabled | PASS, 200 tests, 70.910s |
| Django check | PASS, one existing silenced check |
| makemigrations --check --dry-run | PASS, no changes detected |
| JavaScript tests | PASS, including stale AJAX responses |
| git diff --check | PASS; existing LF/CRLF notices |
| Complete 8,186-row source subset dry-run | PASS, exactly 406 accepted, zero errors/would-create |
| Fixture regenerated from complete source subset | PASS, identical to final fixture |
| Backup restore / full-copy sync + repeat | PASS; application DB unchanged |

The complete-subset skip counters are sequential: 6 invalid barcodes, 827
remaining exclusions, 6,917 invalid scores, 30 outside the manifest. These differ
from the historical score-first recovery counters because exclusions and barcode
checks now run first; they select exactly the same approved 406 identities.
Existing warning: local staticfiles directory absent in view tests. AXES
failed-login/lockout messages are expected auth test output. No actual secret was
read: dotenv was disabled and tests used a generated process-only key.

Tests cover default fixture membership, grades, CSV parity, all 62 overrides,
rejection of nonmembers/missing grades/wrong country, repeated import, manual
ownership/status, ProductView/corrections, atomic rollback and repeat sync.
Synthetic parser/mapping unit tests isolate membership with a mock; the dedicated
manifest/406 integration tests exercise the real policy without that mock.

Enable the actual CSV integration test:

```powershell
$env:PILIHYUK_FINAL_CSV = 'PATH_TO_FINAL_CSV'
.venv/Scripts/python.exe manage.py test product_catalog
.venv/Scripts/python.exe manage.py test
```

Runtime code, timeout/retry, quota, JSON/AJAX regressions and authentication are
unchanged. Runtime still permits unknown scores and rejects all 889 excluded
barcodes, including the 62 now allowed for seeding. Consequently a seeded member
may appear in catalog/detail while barcode lookup rejects it. Runtime may also
import nonmembers of the seed manifest. This boundary has an explicit regression
test and requires the separately deferred team runtime decision; do not claim a
permanently closed 406-only runtime catalog or full integration readiness.
PRD/HANDOFF do not mandate known runtime scores. Four-of-six decision 16 and
K-12/K-13 remain historical/unresolved project text; they were not rewritten.
PostgreSQL/PWS, real browser and external shelf/correction relationships remain
integration checks. No schema change or new dependency was needed.
