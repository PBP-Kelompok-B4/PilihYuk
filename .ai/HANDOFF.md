# Handoff: PilihYuk (PBP midterm project)

Date: 2026-10-31. Project state, notes that live nowhere else, and open items. `README.md` in this folder indexes the other docs.

## Goal

A Django app that compares nutrition and environmental impact of food and drink products inside a user-made shelf. Five members build one module each, and every module covers the course's seven "Aturan Khusus". Data comes from Open Food Facts (OFF), limited to products sold in Indonesia. Final submission: 30 October 2026, 23.59 WIB.

## Current state

Other members' progress is read from Git metadata only, so it says nothing about whether their code works.

- **`main`** is live on PWS with all five modules (deploy of 28 October). PWS has no public shelf yet, so the landing page shows its empty state. The `Procfile` release step runs `collectstatic` and `migrate`, and `seed_products` was run by hand. Email variables are set, so reset mail is sent.
- **`dev`** is ahead of `main`: the `SECURE_PROXY_SSL_HEADER` commit, Modul 3 (PR #15), and the 29 and 30 October work below. 525 tests pass (7 browser tests in `preferences` skip without Chrome), coverage about 93%. This file does not record whether the PR from `dev` to `main` is merged.
- **Audit**: Modul 1, 2, 4 and 5 meet the seven Aturan Khusus (28 October, code and browser). Modul 3 was checked on 30 October and got a filter, sort and pagination on its list. Left thin on purpose: Modul 4 has no owner edit (update happens in curator review), the Modul 3 list is not AJAX, `accounts` has no JSON, and `product_catalog.js` is small.
- **Times**: the database stores UTC. `pilihyuk/middleware.py` activates the browser's time zone from a `tz` cookie that a script in `base.html` sets from `Intl`, so `|date` and `|time` show local time. A missing or bad cookie falls back to UTC, and `tzdata` is in `requirements.txt` for PWS.
- **Modul 1 (Yasmin)** is in `dev`, with the landing page and phone layout. **Landing page**: the table shows the most saved public shelf with at least two active products, and "Shelf pilihan" lists up to four such shelves. Without a public shelf it falls back to four catalog products ("Contoh dari katalog").
- **Modul 2 (Daffaa)**: CRUD at `/shelf/`, AJAX add and remove on the edit page (at most 12 products), a comparison table for up to 4 checked products, and "Simpan ke Shelf Saya". The table follows the viewer's Modul 5 preferences, has a "Pilih ini" button that records a `Decision`, and links empty or `unknown` cells to the Modul 4 correction form. Private shelves return 404 to others, and owners are shown by first name because the username is often the email.
- **Modul 3 (Rafael)**, Git name `Arlen`: app `recommendations`, models `Recommendation` and `RecommendationVote`. PR #8 added list, create and detail, and PR #15 added voting, CRUD and JSON. On 29 and 30 October the user asked for edits in this module: vote buttons show the current choice, authors cannot vote on their own recommendation (403), recommendations with inactive products are hidden, votes run in `transaction.atomic()` with `select_for_update()`, and the list has `q` search, `urutan=skor` sort, pagination (10 per page) and the author's first name for logged-in users only. Tell Rafael before merging.
- **Modul 4 (Rayyan)**, Git name `muhrayyan43`: queue `/antrean/`, submit form `/antrean/produk/<pk>/ajukan/?field=...`, own corrections `/antrean/saya/`, curator queue `/moderasi/`, AJAX on every page. It is mounted once at `''` in `pilihyuk/urls.py`.
- **Modul 5 (Jonathan)**, Git names `Kobaneru` and `JonathanSS`: `/preferensi/` with an AJAX preview, `/keputusan/` with private decisions, and `preferences/ranking.py`. Contract in `preferences/NOTES.md`.
- **Auth**: login accepts email or username, passwords need letters and digits, reset by email works on PWS. django-axes locks 15 minutes after 5 failures per typed value.
- **Deploy**: every commit on `main` goes to PWS (https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/), with `PRODUCTION=True`, `SECRET_KEY` and an admin account that is also the curator.
- **Code facts**: `base.html` has blocks `meta` and `content`. PostgreSQL when `PRODUCTION=True`, SQLite otherwise. `DEBUG = not PRODUCTION`. WhiteNoise, `LANGUAGE_CODE = 'id'`.
- **Shared UI**: `components/tailwind.html` defines `btn-secondary`, `back-link` and `nav-chip`. `nav-link` and `nav-chip` mark the current page with `aria-current` and `bg-mint text-brand`, and the header sets it from `request.resolver_match.namespace`. Paginations outside Modul 4 use `nav-chip` and are centered. The two add-product pages share `product_catalog/_add_tabs.html`.
- **404 for JSON clients**: `handler404` points to `pilihyuk.views.not_found`. `Accept: application/json` or `?format=json` gets `{"error": "Tidak ditemukan."}`, anything else gets `404.html`, both with `Vary: Accept`. With `DEBUG = True` Django shows its own 404 page, so test this with the test client.
- **Decision history URL**: Modul 5 routes moved from `riwayat/` to `keputusan/` on 29 October. `/riwayat/` returns 404 with no redirect, and `decision_bulk_delete` answers 404 for ids owned by someone else. `/katalog/riwayat/` is the product history.

## Notes that live nowhere else

- **Docs layout.** Team docs sit in `.ai/`: project files at the top, per-module folders beside them, and helper files in `<module>/helpers/`. `product_catalog/seed/fixture_data.py` reads `.ai/product_catalog/helpers/off-samples/q1_v2_search_sample.json` (line 14), so moving that file means changing the path there. The ERD lives only in the Drive link in the root README (`.ai/erd/` was removed on 31 October), and PRD section 7 matches the models.
- **`product_catalog` layout** (31 October). `seed/` holds the OFF mapping (`off_mapping.py`), seed eligibility (`name_eligibility.py`, `seed_dataset.py`, `seed_exclusions.py`), the two manifests (`off_seed_dataset.json`, `off_seed_exclusions.json`) and the fixture builder (`fixture_data.py`). `test_suites/` holds every test except `tests.py`, plus the JS client test (`node product_catalog/test_suites/test_catalog_client.cjs`). It is not called `tests/` because a package of that name would clash with `tests.py`. Runtime code (`lookup.py`, `views.py`, `open_food_facts.py`) stays at the top level.
- **Login.** The form looks up the username first. If the input is an email that is not a username, it finds the single account with that email, so an admin from `createsuperuser` can use either. Accounts from Daftar use the email as username, and the display name is not a username (a login with "ardaf" failed on PWS for that reason).
- **Comparison table.** `shelves/comparison.py` builds the rows. Protein and fiber rank higher as better, sugar, sodium and saturated fat lower as better. Energy, fat, carbohydrates, packaging and origin are not ranked. A row marks a best value only when at least two values can be ranked and they are not all equal. `"unknown"` and `"not-applicable"` show as they are, empty fields show "Tidak diketahui". With active Modul 5 preferences, those rows move up (higher weight first) and follow the preferred direction, so energy can be ranked. "Pilih ini" posts `product`, `shelf` and every compared id as `compared_product_ids` to `preferences:decision_create` and works without JavaScript. Empty cells in correctable rows link to `data_correction:submit` with `?field=`.
- **Shelf JSON.** `/shelf/<pk>/?format=json` returns products, compared ids, table rows and whether the viewer saved the shelf. `/kandidat/`, `/produk/`, `/produk/<id>/hapus/` and `/simpan/` answer JSON on `Accept: application/json`.
- **Favicon.** `static/img/favicon.svg` is the header scale on the brand green. `scale.svg` alone has white strokes and disappears on a light tab.
- **Shared pages follow Figma** (file `6CwhelVNc1lJ9XWB4OnYlc`, desktop frames 02 to 14 on page `Wireframe`, phone frames 01 to 15 in section `MOBILE`). On a phone, auth shows the form first, the navbar is logo, search and menu, and the footer columns fold. Not checked against Figma mobile 02: the phone position of "Lihat semua shelf".
- **Seeding** uses 406 products with an official Nutri-Score, not the 196 of PRD decision 16. The group still has to pick a rule.
- **`product_catalog/helpers/tools/check_off_encodings.py`** is the research script behind `is_sold_in_indonesia()` and `normalize_barcode()`.
- **Root `CLAUDE.md`** is git-ignored and only loads `.private/CLAUDE.md`, which teammates do not have.

## Pitfalls

- django-axes makes `Client.login()` fail in tests. Use `force_login`. A view that calls `login()` must pass `backend=`.
- Run tests with the project virtualenv (`env/Scripts/python.exe manage.py test`).
- Read `product_catalog/off-api-findings.md` before touching the OFF client.
- `Meta.ordering` is ignored on a queryset with `annotate(Count(...))`. Add `order_by()` before paginating.
- The `tz` cookie must hold the raw zone name (`Asia/Jakarta`), because Django does not URL-decode cookies.
- The PWS log warns `No directory at: /app/staticfiles/`. It is harmless: `WHITENOISE_USE_FINDERS = True` serves static files.

## Open items

- Merge the proxy-header PR into `main`, then run `curl -sI https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/masuk/ | grep -i strict-transport`. Output means HTTPS is recognised and reset mail links use `https://`. Keep `SECURE_SSL_REDIRECT` and a per-IP lockout off until that header shows.
- Create 2 or 3 public shelves on PWS (each with at least two products) and save one, so the landing page shows real shelves. Then test every flow on PWS once.
- Modul 3: test pagination of `/rekomendasi/` with real data and re-audit it against the seven Aturan Khusus.
- The footer links `/tentang/`, `/panduan/`, `/kebijakan-data/` and `/kontak/` have no page in Figma or the PRD and show the custom 404.
- K-7 (Redis) is not studied. PRD section 14 lists what is still unverified.
