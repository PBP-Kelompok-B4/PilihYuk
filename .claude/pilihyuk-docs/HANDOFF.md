# Handoff: PilihYuk (PBP midterm group project)

Date: 2026-10-06. State of the project, notes that live nowhere else, and open items. The other docs own the rest: `../README.md` indexes them, `PRD.md` has requirements and all decisions, `timeline.md` has the schedule and per-person tasks, and the OFF findings are in `off-api-findings.md`.

## Goal

A Django app, "PilihYuk", that compares nutrition and environmental impact of food and drink products grouped in a user-made shelf. Five members, one module each, every module covering the course's seven "Aturan Khusus". Final submission: 23 October 2026, 23.59 WIB. Data source: Open Food Facts (OFF), limited to products sold in Indonesia.

## Current state

- **`main` (deployed to PWS):** the scaffold, six registered apps, empty template and JS folders per app, the landing page, and the app rename (`catalog` to `product_catalog`, `dataflags` to `data_correction`).
- **`dev`, not on `main` yet:** auth (`accounts`), finished 4 October: register, login, logout, profile, django-axes, the `Procfile`, and the `SECRET_KEY` and `DEBUG` settings. `accounts` has 34 tests (37 in the project) and passed the security and Django reviews.
- **Tailwind:** CDN script, no CLI or build step. `base.html` includes `templates/components/tailwind.html` (theme, shared classes, script tag). Pages need internet. Checked on 6 October at localhost:8000 (landing page and `/masuk/`): colors, font, `btn-brand` and the dynamic `bg-nutri-*` classes apply, with no horizontal overflow. The only console error is a missing `favicon.ico`.
- **Deploy:** `deploy.yml` pushes every commit on `main` to PWS (https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/), so a broken `main` breaks the live site. `PRODUCTION=True` and `SECRET_KEY` are set on PWS.
- **Code facts:** `base.html` has blocks `meta` and `content`. `settings.py` uses PostgreSQL when `PRODUCTION=True` and SQLite locally, `DEBUG = not PRODUCTION`, `SECRET_KEY` from the environment with no fallback, WhiteNoise, `LANGUAGE_CODE = 'id'`, and django-axes.

## Notes that live nowhere else

- **ERD files.** `erd/pilihyuk.drawio` is the main file. Edit it in draw.io and update the Mermaid block by hand, because the script that generated them is not in the repo. The Google Drive copy linked in the README has the current version.
- **`drafts/product_catalog/`.** Hand-over files for Yasmin (`open_food_facts.py`, `tests.py`, a README). They stay out of `product_catalog/` on purpose so she commits Modul 1 code herself (individual grading). The 5 tests mock the network and only run once the file sits in `product_catalog/`. The 3 lookups per minute limit is missing on purpose, because it belongs in the view.
- **`tools/check_off_encodings.py`.** The original research script (`--csv`, `--dump`, `--selftest`). Its `normalize_barcode()` and `is_indonesian()` became `is_sold_in_indonesia()` in the app.
- **Tailwind decision.** Chosen after reading the Figma wireframe (file `6CwhelVNc1lJ9XWB4OnYlc`, page `Wireframe`, node 6:3). Bootstrap stays valid if the team prefers it (PRD decision 28).

## Pitfalls

- With django-axes, `Client.login()` in tests fails because it sends no `request`. Log in through the form or use `force_login`. A view that calls `login()` must pass `backend=`, since two backends are configured.
- Tests need the project's virtualenv. The system Python fails with `No module named 'axes'`. On Windows: `env/Scripts/python.exe manage.py test`.
- How OFF really behaves (grade field names, `"unknown"` instead of `null`, the `id` subdomain not filtering v3, search coverage bias, 503 returning HTML) is in `off-api-findings.md`. Read it before touching the OFF client.

## Open items

- Merge `dev` into `main` once the Tailwind CDN switch is committed, then read the first PWS deploy log. The `Procfile` release step is untested, and its content comes from a summary of the PWS docs. If the auth, sessions or axes tables are missing, run `migrate` by hand on PWS.
- Send Yasmin the folder `drafts/product_catalog/`.
- Seeding is not final (PRD decision 16, K-12, K-13).
- Test on the real PWS proxy before turning on `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT` or a per-IP lockout. Test auth on PostgreSQL and on a real phone.
- The wireframe footer lacks the license wording (ODbL, CC BY-SA) and a link target to https://openfoodfacts.org. The code or the "Kebijakan data" page can add them.
- The team will add mobile frames and the "Lihat di Open Food Facts" link to the wireframe. The mobile proposal (comparison table with 2 products per screen and horizontal scroll) is not final.
- Confirm Tailwind with the team. K-7 (Redis) is not studied yet. The list of untested OFF behavior is in PRD section 14.
