# Handoff: PilihYuk (PBP midterm group project)

Date: 2026-10-24. This file holds the project state, notes that live nowhere else, and open items. `../README.md` indexes the other docs: `PRD.md` has requirements and decisions, `timeline.md` has branch status and tasks per person, and `off-api-findings.md` has the Open Food Facts (OFF) findings.

## Goal

PilihYuk is a Django app that compares nutrition and environmental impact of food and drink products inside a user-made shelf. Five members build one module each, and every module must cover the course's seven "Aturan Khusus". Data comes from OFF, limited to products sold in Indonesia. Final submission is 30 October 2026, 23.59 WIB.

## Current state

Other members' progress is read from Git metadata only (commit messages, file names, branch positions), so it says nothing about whether their code works.

- **`main`** is live on PWS since 23 October with auth, Modul 1, the shared pages and the Rekomendasi rename. The `Procfile` release step ran `migrate`. `seed_products` had to be run by hand in the PWS terminal. Pages work on desktop and on a phone.
- **`dev`** is `main` plus the Modul 2 models. 163 tests pass.
- **Modul 1 (Yasmin)** is in `dev`. Two later commits (landing page products, phone layout) are still only on her branch.
- **Modul 2 (Daffaa)**: models are in `dev`. Branch `shelves` adds CRUD at `/shelf/`: public list with search and JSON, Shelf Saya, create, edit, delete and detail. Private shelves return 404 to others, and owners are shown by first name because the username is the email. Not done yet: adding products by AJAX, the comparison table, saving shelves and `featured_shelves()` on the landing page.
- **Modul 3 (Rafael)** lives on branch `recommendations` under the Git name `Arlen` (Rafael's middle name), still in the `substitutions` app folder. It has the `Substitution` model, views, templates and tests. No vote model or JS yet. Not in `dev`.
- **Modul 4 (Rayyan)** is the largest branch: models, validators, multi-field corrections, curator and contribution queues, JSON responses and many tests. `data_correction.js` is still empty. Not in `dev`.
- **Modul 5 (Jonathan)** has no code yet. The `Shelf` model it needs is now in `dev`.
- **Deploy**: `deploy.yml` pushes every commit on `main` to PWS (https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/), so a broken `main` breaks the live site. PWS has `PRODUCTION=True` and `SECRET_KEY`. Its admin account is also the curator (`is_staff`).
- **Code facts**: `base.html` has blocks `meta` and `content`. `settings.py` uses PostgreSQL when `PRODUCTION=True` and SQLite otherwise, `DEBUG = not PRODUCTION`, `SECRET_KEY` from the environment with no fallback, WhiteNoise, `LANGUAGE_CODE = 'id'` and django-axes.

## Notes that live nowhere else

- **Login uses the username field.** Accounts from the register page have username = email, so email login works. An admin made with `createsuperuser` and a different username can only log in with that username. Set its username to its email to fix that.
- **Rekomendasi rename.** The README, docs, header, footer, landing page and Figma (text and layer names) say "Rekomendasi". Code names stay `substitutions` and `Substitution`. The navbar links to `/rekomendasi/`, so Modul 3 must mount there.
- **Shared pages follow Figma.** On a phone, auth shows the form first and the brand panel below it (frame 13 was reordered in Figma to match), the navbar is logo, search and menu, and the footer links sit inline. `.row-label` and the first column of the landing table are sticky, so 2 products fit per screen. Still missing: the footer accordion and the phone position of "Lihat semua shelf".
- **Figma** (file `6CwhelVNc1lJ9XWB4OnYlc`): desktop frames 02 to 14 on page `Wireframe` (node `6:3`), phone frames 01 to 15 in section `MOBILE` (node `180:34276`). Frame 06 on a phone shows the comparison table with 2 products per screen, horizontal scroll and a sticky metric column.
- **Seeding** uses 406 products with an official Nutri-Score a to e, not the 196 with at least 4 of 6 comparison rows in PRD decision 16. By the same rule, 165 of the 406 have 4 rows (41%), so the PRD target of 70% fails. The group still has to pick a rule.
- **ERD**: `erd/pilihyuk.drawio` is the source. Update the Mermaid block by hand. It has not been checked against the models the modules wrote.
- **Archives**: `drafts/product_catalog/` was the hand-over for Yasmin and is no longer used. `tools/check_off_encodings.py` is the research script behind `is_sold_in_indonesia()`.

## Pitfalls

- django-axes makes `Client.login()` fail in tests. Use `force_login` or log in through the form. A view that calls `login()` must pass `backend=`.
- Run tests with the project virtualenv (`env/Scripts/python.exe manage.py test`). The system Python lacks `axes`.
- Read `off-api-findings.md` before touching the OFF client. It covers grade field names, `"unknown"` instead of `null`, and 503 responses that return HTML.

## Open items

- Merge `shelves` CRUD, Modul 3 and Modul 4 into `dev`, then `dev` into `main`.
- Test on the real PWS proxy before turning on `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT` or a per-IP lockout.
- Create a curator account without superuser rights if the demo needs one.
- K-7 (Redis) is not studied. PRD section 14 lists untested OFF behavior.
