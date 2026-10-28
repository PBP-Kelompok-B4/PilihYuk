# Handoff: PilihYuk (PBP midterm group project)

Date: 2026-10-28. This file holds the project state, notes that live nowhere else, and open items. `README.md` in this folder indexes the other docs.

## Goal

PilihYuk is a Django app that compares nutrition and environmental impact of food and drink products inside a user-made shelf. Five members build one module each, and every module must cover the course's seven "Aturan Khusus". Data comes from Open Food Facts (OFF), limited to products sold in Indonesia. Final submission is 30 October 2026, 23.59 WIB.

## Current state

Other members' progress is read from Git metadata only, so it says nothing about whether their code works.

- **`main`** is live on PWS. The last deploy (27 October, PR #9) added Modul 2 and Modul 3. The `Procfile` release step runs `collectstatic` and `migrate`. `seed_products` was run by hand in the PWS terminal. The email variables are set, so reset mail is sent for real.
- **`dev`** has all five modules, the custom 404 page, the footer accordion and these docs. 506 tests pass (7 browser tests in `preferences` skip without Chrome). Modul 4, Modul 5 and the latest fixes are not on `main` yet.
- **Times**: the database stores UTC (`USE_TZ = True`, `TIME_ZONE = 'UTC'`). `pilihyuk/middleware.py` activates the browser's time zone from a `tz` cookie that a small script in `base.html` sets from `Intl`, so every `|date` and `|time` in every module shows local time. A missing or bad cookie falls back to UTC. `tzdata` is in `requirements.txt` so `zoneinfo` works on PWS even without a system zone database.
- **Modul 1 (Yasmin)** is in `dev`, including the landing page and phone layout commits.
- **Landing page**: the table shows the most saved public shelf with at least two active products, and "Shelf pilihan" lists up to four such shelves. With no public shelf the table falls back to four catalog products labelled "Contoh dari katalog", and the shelf section says "Belum ada shelf publik saat ini".
- **Modul 2 (Daffaa)** is in `dev`. It has CRUD at `/shelf/`, adding and removing products by AJAX on the edit page (active candidates searched in the database, at most 12), a comparison table on the detail page for up to 4 checked products, and "Simpan ke Shelf Saya" by AJAX. The table follows the viewer's Modul 5 preferences and has a "Pilih ini" button that records a `Decision`. Empty or `unknown` values in the table link to the Modul 4 correction form. Create, edit, delete and Shelf Saya also answer JSON. Private shelves return 404 to others. Owners are shown by first name because the username is often the email.
- **Modul 3 (Rafael)** is in `dev` since 27 October (PR #8, Git name `Arlen`, Rafael's middle name). The app is now `recommendations` with models `Recommendation` and `RecommendationVote`, and `/rekomendasi/` has list, create and detail. There is no vote, edit or delete route yet, and `recommendations.js` is empty.
- **Modul 4 (Rayyan)** is in `dev` (Git name `muhrayyan43`): contribution queue at `/antrean/`, submit form at `/antrean/produk/<pk>/ajukan/?field=...`, own corrections at `/antrean/saya/`, curator queue at `/moderasi/`, AJAX on every page. Its routes already start with `antrean/` and `moderasi/`, so `pilihyuk/urls.py` mounts it once at `''`. A second `include` at `antrean/` left over from the skeleton broke 32 of its tests until 28 October.
- **Modul 5 (Jonathan)** is in `dev` since 27 October (PR #10, Git names `Kobaneru` and `JonathanSS`): `/preferensi/` with an AJAX preview, `/riwayat/` with private decisions, and `preferences/ranking.py`. Its contract is in `preferences/NOTES.md`. That file still says the shelf integration is not installed, which is no longer true.
- **Auth** (24 October): login accepts email or username, passwords need letters and digits, and the terms checkbox and the disabled Google button are gone. Figma frames 12 and 13 match.
- **Deploy**: every commit on `main` goes to PWS (https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/). PWS has `PRODUCTION=True`, `SECRET_KEY` and an admin account that is also the curator.
- **Code facts**: `base.html` has blocks `meta` and `content`. PostgreSQL when `PRODUCTION=True`, SQLite otherwise. `DEBUG = not PRODUCTION`. WhiteNoise, `LANGUAGE_CODE = 'id'`, django-axes.

## Notes that live nowhere else

- **Docs layout.** All team docs sit directly in `.claude/`. `off-samples/q1_v2_search_sample.json` is also read by `product_catalog/fixture_data.py`, whose tests build a fixture from it, so moving it means changing line 14 there (done on 24 October with the user's approval; tell Yasmin).
- **Login.** The form looks up the username first. If the input is an email that is not a username, it finds the single account with that email, so an admin from `createsuperuser` can log in with either. Accounts from Daftar use the email as username, and the display name is not a username: on 27 October a login with the display name "ardaf" failed on PWS for that reason, not because of a bug. django-axes locks per typed value.
- **Rekomendasi rename.** README, docs, header, footer, landing page and Figma say "Rekomendasi". Since 27 October the code uses the same name: app `recommendations`, models `Recommendation` and `RecommendationVote`, mounted at `/rekomendasi/`.
- **Comparison table.** `shelves/comparison.py` builds the rows. Protein and fiber rank higher as better. Sugar, sodium and saturated fat rank lower as better. Energy, fat and carbohydrates are not ranked, and neither are packaging and origin. A row marks a best value only when at least two values can be ranked and they are not all equal. `"unknown"` and `"not-applicable"` show as they are, and empty fields show "Tidak diketahui". When the viewer has active Modul 5 preferences, those nutrient rows move up (higher weight first) and their best value follows the preferred direction, so energy can be ranked too. The "Pilih ini" form posts `product`, `shelf` and every compared id as `compared_product_ids` to `preferences:decision_create`, and works without JavaScript. Empty cells in correctable rows (NOVA, the eight nutrients, origin) link to `data_correction:submit` with `?field=`, and an `unknown` score links to the same form without a field. Packaging and `not-applicable` get no link.
- **Shelf JSON.** `/shelf/<pk>/?format=json` returns the products, the compared ids, the table rows and whether the viewer saved the shelf. `/shelf/<pk>/kandidat/`, `/produk/`, `/produk/<id>/hapus/` and `/simpan/` answer JSON when the request sends `Accept: application/json`.
- **Favicon.** `static/img/favicon.svg` is the header scale on the brand green. `scale.svg` alone has white strokes and disappears on a light tab.
- **Shared pages follow Figma.** On a phone, auth shows the form first and the brand panel below it, the navbar is logo, search and menu, and the footer links sit inline. `.row-label` and the first column of the landing table are sticky. The footer columns are `<details>` elements, so they fold on a phone and stay open on desktop. Not yet checked against Figma mobile 02: the phone position of "Lihat semua shelf".
- **Figma** (file `6CwhelVNc1lJ9XWB4OnYlc`): desktop frames 02 to 14 on page `Wireframe` (node `6:3`), phone frames 01 to 15 in section `MOBILE` (node `180:34276`).
- **Seeding** uses 406 products with an official Nutri-Score, not the 196 with 4 of 6 comparison rows in PRD decision 16. The group still has to pick a rule.
- **ERD**: the Mermaid block in `erd/pilihyuk-erd.md`, the draw.io file and PRD section 7 match the models of all five modules in `dev` as of 28 October. `erd/pilihyuk.drawio` and its PNG were updated the same day (a script edited the XML and the official draw.io viewer rendered the PNG). The Drive file linked from README was replaced with the new PNG.
- **`tools/check_off_encodings.py`** is the research script behind `is_sold_in_indonesia()` and `normalize_barcode()`. The old `drafts/` hand-over for Yasmin was deleted, since her module has its own versions.
- **Root `CLAUDE.md`** is git-ignored. It only loads `.private/CLAUDE.md`, which teammates do not have.

## Pitfalls

- django-axes makes `Client.login()` fail in tests. Use `force_login` or log in through the form. A view that calls `login()` must pass `backend=`.
- Run tests with the project virtualenv (`env/Scripts/python.exe manage.py test`).
- Read `off-api-findings.md` before touching the OFF client.
- Since Django 3.1, `Meta.ordering` is ignored on a queryset with `annotate(Count(...))`. Add `order_by()` before paginating, or pages come back in random order (`UnorderedObjectListWarning` in the log).
- The `tz` cookie must hold the raw zone name (`Asia/Jakarta`). Django does not URL-decode cookies, so an encoded `Asia%2FJakarta` silently falls back to UTC.
- The PWS log warns `No directory at: /app/staticfiles/`. `collectstatic` runs in the release container, and `WHITENOISE_USE_FINDERS = True` serves static files anyway, so it is harmless.

## Open items

- Merge `dev` into `main` so Modul 4, Modul 5 and the latest fixes go live, then test every flow on PWS and create a few public shelves as demo data.
- Modul 3 still needs voting by AJAX (Aturan Khusus 5) and its edit and delete views. `recommendations.js` is empty.
- `preferences/NOTES.md` still says the shelf integration is not installed. Jonathan should update it.
- The footer links `/tentang/`, `/panduan/`, `/kebijakan-data/` and `/kontak/` have no page in Figma or the PRD. They show the custom 404 for now.
- Reset password works on PWS since 27 October (`/lupa-password/`, Gmail with an app password). New environment variables only apply after a redeploy. The links in the mail still start with `http://` until `SECURE_PROXY_SSL_HEADER` is set. Figma frames 12 and 13 have the "Lupa password?" link and both reset screens, laid out in two rows so the frames do not overlap their neighbours.
- Test on the real PWS proxy before turning on `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT` or a per-IP lockout.
- K-7 (Redis) is not studied. PRD section 14 lists what is still unverified.
