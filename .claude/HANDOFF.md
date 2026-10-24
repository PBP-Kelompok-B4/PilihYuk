# Handoff: PilihYuk (PBP midterm group project)

Date: 2026-10-24. This file holds the project state, notes that live nowhere else, and open items. `README.md` in this folder indexes the other docs.

## Goal

PilihYuk is a Django app that compares nutrition and environmental impact of food and drink products inside a user-made shelf. Five members build one module each, and every module must cover the course's seven "Aturan Khusus". Data comes from Open Food Facts (OFF), limited to products sold in Indonesia. Final submission is 30 October 2026, 23.59 WIB.

## Current state

Other members' progress is read from Git metadata only, so it says nothing about whether their code works.

- **`main`** is live on PWS since 23 October with auth, Modul 1, the shared pages and the Rekomendasi rename. The `Procfile` release step ran `migrate`, and `seed_products` was run by hand in the PWS terminal.
- **`dev`** adds all of Modul 2, the auth changes of 24 October, the favicon and these docs. 196 tests pass.
- **Modul 1 (Yasmin)** is in `dev`. Two later commits (landing page products, phone layout) are still only on her branch.
- **Modul 2 (Daffaa)** is in `dev`. It has CRUD at `/shelf/`, adding and removing products by AJAX on the edit page (active candidates searched in the database, at most 12), a comparison table on the detail page for up to 4 checked products, and "Simpan ke Shelf Saya" by AJAX. Private shelves return 404 to others. Owners are shown by first name because the username is often the email. Still open: `featured_shelves()` on the landing page and the links to Modul 4 and Modul 5.
- **Modul 3 (Rafael)** lives on branch `recommendations` under the Git name `Arlen` (Rafael's middle name), still in the `substitutions` app folder. No vote model or JS yet. Not in `dev`.
- **Modul 4 (Rayyan)** is the largest branch and not in `dev`. `data_correction.js` is still empty.
- **Modul 5 (Jonathan)** has no code yet. The `Shelf` model it needs is in `dev`.
- **Auth** (24 October): login accepts email or username, passwords need letters and digits, and the terms checkbox and the disabled Google button are gone. Figma frames 12 and 13 match.
- **Deploy**: every commit on `main` goes to PWS (https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/). PWS has `PRODUCTION=True`, `SECRET_KEY` and an admin account that is also the curator.
- **Code facts**: `base.html` has blocks `meta` and `content`. PostgreSQL when `PRODUCTION=True`, SQLite otherwise. `DEBUG = not PRODUCTION`. WhiteNoise, `LANGUAGE_CODE = 'id'`, django-axes.

## Notes that live nowhere else

- **Docs layout.** All team docs sit directly in `.claude/`. `off-samples/q1_v2_search_sample.json` is also read by `product_catalog/fixture_data.py`, whose tests build a fixture from it, so moving it means changing line 14 there (done on 24 October with the user's approval; tell Yasmin).
- **Login.** The form looks up the username first. If the input is an email that is not a username, it finds the single account with that email, so an admin from `createsuperuser` can log in with either. django-axes still locks per account.
- **Rekomendasi rename.** README, docs, header, footer, landing page and Figma say "Rekomendasi". Code names stay `substitutions` and `Substitution`. The navbar links to `/rekomendasi/`, so Modul 3 must mount there.
- **Comparison table.** `shelves/comparison.py` builds the rows. Protein and fiber rank higher as better. Sugar, sodium and saturated fat rank lower as better. Energy, fat and carbohydrates are not ranked, and neither are packaging and origin. A row marks a best value only when at least two values can be ranked and they are not all equal. `"unknown"` and `"not-applicable"` show as they are, and empty fields show "Tidak diketahui". Preference ordering (Modul 5) can reorder the list that `comparison_rows()` returns, and the correction link (Modul 4) belongs in the cells whose `rank` is `None` in `templates/shelves/_comparison.html`.
- **Shelf JSON.** `/shelf/<pk>/?format=json` returns the products, the compared ids, the table rows and whether the viewer saved the shelf. `/shelf/<pk>/kandidat/`, `/produk/`, `/produk/<id>/hapus/` and `/simpan/` answer JSON when the request sends `Accept: application/json`.
- **Favicon.** `static/img/favicon.svg` is the header scale on the brand green. `scale.svg` alone has white strokes and disappears on a light tab.
- **Shared pages follow Figma.** On a phone, auth shows the form first and the brand panel below it, the navbar is logo, search and menu, and the footer links sit inline. `.row-label` and the first column of the landing table are sticky. Still missing: the footer accordion and the phone position of "Lihat semua shelf".
- **Figma** (file `6CwhelVNc1lJ9XWB4OnYlc`): desktop frames 02 to 14 on page `Wireframe` (node `6:3`), phone frames 01 to 15 in section `MOBILE` (node `180:34276`).
- **Seeding** uses 406 products with an official Nutri-Score, not the 196 with 4 of 6 comparison rows in PRD decision 16. The group still has to pick a rule.
- **ERD**: `erd/pilihyuk.drawio` is the source. Update the Mermaid block by hand. It has not been checked against the models the modules wrote.
- **`tools/check_off_encodings.py`** is the research script behind `is_sold_in_indonesia()` and `normalize_barcode()`. The old `drafts/` hand-over for Yasmin was deleted, since her module has its own versions.
- **Root `CLAUDE.md`** is git-ignored. It only loads `.private/CLAUDE.md`, which teammates do not have.

## Pitfalls

- django-axes makes `Client.login()` fail in tests. Use `force_login` or log in through the form. A view that calls `login()` must pass `backend=`.
- Run tests with the project virtualenv (`env/Scripts/python.exe manage.py test`).
- Read `off-api-findings.md` before touching the OFF client.

## Open items

- Merge Modul 3 and Modul 4 into `dev`, then `dev` into `main`.
- Modul 2 leftovers: `featured_shelves()` after Yasmin's landing commit, the correction link from `"unknown"`, the "Pilih ini" button that saves a `Decision`, and the "Estimasi" marker for Green-Score in the table.
- Reset password works (`/lupa-password/`). On PWS it only sends mail after `EMAIL_HOST`, `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are set (a project Gmail with an app password). Without them the mail only shows in the PWS log. Figma frames 12 and 13 have the "Lupa password?" link and both reset screens, laid out in two rows so the frames do not overlap their neighbours.
- Test on the real PWS proxy before turning on `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT` or a per-IP lockout.
- K-7 (Redis) is not studied. PRD section 14 lists what is still unverified.
