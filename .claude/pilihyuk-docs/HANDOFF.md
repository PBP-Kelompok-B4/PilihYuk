# Handoff: PilihYuk (PBP midterm group project)

Date: 2026-10-23. State of the project, notes that live nowhere else, and open items. The other docs own the rest: `../README.md` indexes them, `PRD.md` has requirements and all decisions, `timeline.md` has the schedule, the per-branch status and per-person tasks, and the OFF findings are in `off-api-findings.md`.

## Goal

A Django app, "PilihYuk", that compares nutrition and environmental impact of food and drink products grouped in a user-made shelf. Five members, one module each, every module covering the course's seven "Aturan Khusus". Final submission: 30 October 2026, 23.59 WIB (moved from 23 October). Data source: Open Food Facts (OFF), limited to products sold in Indonesia.

## Current state

Branch progress below comes from Git metadata only (commit messages, changed file names, branch positions). Nobody has opened, run or tested the code of the other branches for this summary.

- **`main` (deployed to PWS), last change 6 October:** the scaffold, landing page, Tailwind CDN, auth (PR #1) and these docs (PR #2). No feature module yet.
- **`dev`:** `main` plus Modul 1 (PR #4, merged 20 October). 5 commits ahead of `main`, never pushed to `main`.
- **Modul 1 (`product_catalog`, Yasmin):** in `dev`. Models, OFF client, barcode lookup with a quota table, manual entry, view history, list and detail pages, and a reviewed 406-product seed. Two later commits (landing page products, which touch `pilihyuk/views.py` and `templates/index.html`, and a temporary mobile layout) are only on her branch.
- **Modul 2 (`shelves`, Daffaa):** not started. The app is still the scaffold. The local `shelves` branch already has `dev` merged in and is not pushed.
- **Modul 3 (Rekomendasi Komunitas, Rafael):** the work sits on branch `recommendations` (Git name `Arlen`, which is Rafael), still in the `substitutions` app folder: `Substitution` model and migration, form, views, URLs, three templates, tests, and one line in Yasmin's `product_detail.html`. No vote model or JS seen yet. Not in `dev`. Branch `substitutions` is empty.
- **Modul 4 (`data_correction`, Rayyan):** the largest branch (25 own commits, 21 to 23 October): models and migration, validators, services, multi-field form, user pages, curator queue with per-field review, contribution queue, HTML and JSON responses, a large test file. `static/js/data_correction.js` unchanged. Not in `dev`, but up to date with it.
- **Modul 5 (`preferences`, Jonathan):** not started (only a `.gitignore` change). 4 commits behind `dev`.
- **Auth (`accounts`):** done since 4 October, 34 tests, on `main`.
- **Deploy:** `deploy.yml` pushes every commit on `main` to PWS (https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/), so a broken `main` breaks the live site. `PRODUCTION=True` and `SECRET_KEY` are set on PWS. The local `pws` remote fails with an authentication error, which does not matter because deploys go through GitHub Actions.
- **Code facts:** `base.html` has blocks `meta` and `content`. `settings.py` uses PostgreSQL when `PRODUCTION=True` and SQLite locally, `DEBUG = not PRODUCTION`, `SECRET_KEY` from the environment with no fallback, WhiteNoise, `LANGUAGE_CODE = 'id'`, and django-axes.

## Notes that live nowhere else

- **ERD files.** `erd/pilihyuk.drawio` is the main file. Edit it in draw.io and update the Mermaid block by hand, because the script that generated them is not in the repo. The Google Drive copy linked in the README has the current version. The ERD has not been checked against the models the modules actually wrote.
- **`drafts/product_catalog/`.** The hand-over files for Yasmin. Modul 1 now has its own `product_catalog/open_food_facts.py` in `dev`, so the draft is only an archive.
- **`tools/check_off_encodings.py`.** The original research script (`--csv`, `--dump`, `--selftest`). Its `normalize_barcode()` and `is_indonesian()` became `is_sold_in_indonesia()` in the app.
- **Tailwind decision.** Chosen after reading the Figma wireframe (file `6CwhelVNc1lJ9XWB4OnYlc`, page `Wireframe`, node 6:3). PRD decision 28.

## Pitfalls

- With django-axes, `Client.login()` in tests fails because it sends no `request`. Log in through the form or use `force_login`. A view that calls `login()` must pass `backend=`, since two backends are configured.
- Tests need the project's virtualenv. The system Python fails with `No module named 'axes'`. On Windows: `env/Scripts/python.exe manage.py test`.
- How OFF really behaves (grade field names, `"unknown"` instead of `null`, the `id` subdomain not filtering v3, search coverage bias, 503 returning HTML) is in `off-api-findings.md`. Read it before touching the OFF client.

## Open items

- No fixed schedule lives in the docs. The group sets it in chat.
- Build Modul 2. The `Shelf` model must reach `dev` first, because Jonathan's `Decision` needs it.
- Get Modul 3 and Modul 4 into `dev`, then push `dev` to `main`. On 23 October `dev` (auth, Modul 1, shared pages) reached `main` and PWS: the `Procfile` release step ran, and `python manage.py seed_products` had to be run by hand in the PWS terminal (release does not seed). Pages work on desktop and on a phone. PWS has an admin account, which is also the curator (`is_staff`); a separate curator-only account does not exist yet.
- Seeding: Modul 1 seeds 406 products picked by "official Nutri-Score a to e" (437 minus 30 nameless and 1 bad barcode), not the 196 picked by "at least 4 of 6 comparison rows" in PRD decision 16. Counted on `products-406.json` with the same rule (gizi = 6 of 7 nutrients): 165 of the 406 reach 4 rows, 241 do not (54 have only the Nutri-Score row). So about 31 of the 196 are missing, likely those without a Nutri-Score. Not verified against the dump, which is not on disk. The group decides which rule wins; the PRD success target "70% of seeded products have 4 of 6 rows" fails at 165/406 (41%).
- "Substitusi" became "Rekomendasi" in the README, the docs, the header, the footer and the landing page. The header and footer link to `/rekomendasi/`, so Modul 3 must mount its URLs there. Code names stay (`substitutions` app, `Substitution` model). Figma was renamed on 23 October too: every text and layer name (navbar components, frame `08 — Rekomendasi Komunitas`, mobile frame `08 — Mobile Recommendation`, component `Components / Table Row / Recommendation`).
- Test on the real PWS proxy before turning on `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT` or a per-IP lockout. Test auth on PostgreSQL and on a real phone.
- Shared pages follow Figma since 23 October. Auth puts the brand panel below the form on a phone (frame `13`, reordered in Figma on 23 October to match), the phone navbar is logo, search and menu with Masuk and Daftar inside the menu (frame `02 Mobile Home`), the footer links sit inline on a phone, and `.row-label` plus the first column of the landing table stay sticky so 2 products fit per screen (frame `06`). The footer already carries the license line (ODbL, DbCL, CC BY-SA) and the OFF link. Not done: the footer accordion and the "Lihat semua shelf" button position on a phone.
- Figma now has mobile frames: section `MOBILE` (node `180:34276`) with 15 frames, `01 Mobile Design System` to `15 Mobile States & Modals`, plus "Shelf Saya" variants. `06 Mobile Shelf Comparison` settles the comparison table on a phone: 2 products per screen, horizontal scroll, sticky metric column, at most 4 products. Desktop frames are `02` to `14` on page `Wireframe` (node `6:3`). K-7 (Redis) is not studied yet. The list of untested OFF behavior is in PRD section 14.
