"""Tes browser opsional: PILIHYUK_BROWSER_TESTS=1, Playwright, dan Chrome lokal."""

import importlib.util
import os
import re
import shutil
from pathlib import Path
import unittest

from django.conf import settings
from django.core.cache import cache
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from preferences.models import Decision, Preference
from .helpers import make_product, make_user


CHROME_AVAILABLE = bool(shutil.which("google-chrome") or shutil.which("chrome")) or any(
    (Path(root) / "Google/Chrome/Application/chrome.exe").is_file()
    for root in (os.getenv("PROGRAMFILES", "C:/Program Files"), os.getenv("PROGRAMFILES(X86)", "C:/Program Files (x86)"))
)


@unittest.skipUnless(os.getenv("PILIHYUK_BROWSER_TESTS") == "1" and importlib.util.find_spec("playwright") and CHROME_AVAILABLE,
                     "Tes browser memerlukan opt-in, Playwright, dan Chrome lokal.")
class DecisionBrowserTests(StaticLiveServerTestCase):
    def test_global_draft_reset_and_failed_save_keep_database_unchanged(self):
        from playwright.sync_api import expect, sync_playwright

        user = make_user()
        Preference.objects.create(user=user, nutrient="protein", direction="max", weight=3)
        self.client.force_login(user)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            context.add_cookies([{"name": settings.SESSION_COOKIE_NAME,
                                 "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                                 "url": self.live_server_url}])
            page = context.new_page()
            page.goto(self.live_server_url + "/preferensi/")
            expect(page.get_by_role("button", name="Simpan Preferensi", exact=True)).to_have_count(1)
            page.locator("#active-fiber").click()
            items = page.request.get(self.live_server_url + "/preferensi/", headers={"Accept": "application/json"}).json()["items"]
            self.assertEqual(len(items), 1)
            page.get_by_role("button", name="Reset", exact=True).click()
            expect(page.locator('[role="switch"][aria-checked="true"]')).to_have_count(0)
            page.locator("#active-fiber").click()
            page.get_by_role("button", name="Simpan Preferensi", exact=True).click()
            expect(page.locator('[data-draft-status]')).to_have_text("Semua perubahan tersimpan.")
            items = page.request.get(self.live_server_url + "/preferensi/", headers={"Accept": "application/json"}).json()["items"]
            self.assertEqual([item["nutrient"] for item in items], ["fiber"])
            page.route("**/preferensi/simpan/", lambda route: route.fulfill(status=400, json={"ok": False, "message": "Gagal menyimpan."}))
            page.locator('label', has=page.locator('#weight-fiber-3')).click()
            page.get_by_role("button", name="Simpan Preferensi", exact=True).click()
            expect(page.locator('[data-module-status]')).to_have_text("Gagal menyimpan.")
            expect(page.locator('#weight-fiber-3')).to_be_checked()
            expect(page.locator('[data-draft-status]')).to_have_text("Ada perubahan belum disimpan.")
            browser.close()

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_optimistic_bulk_delete_restores_on_failure(self):
        from playwright.sync_api import expect, sync_playwright

        user = make_user()
        product = make_product()
        for index in range(2):
            Decision.objects.create(user=user, product=product, note=f"Tersimpan {index}")
        self.client.force_login(user)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 390, "height": 900})
            context.add_cookies([{"name": settings.SESSION_COOKIE_NAME,
                                 "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                                 "url": self.live_server_url}])
            page = context.new_page()
            page.goto(self.live_server_url + "/riwayat/")
            page.evaluate("window.modulePage = 'same-page'")
            page.locator('[data-decision-bulk] button').click()
            expect(page.locator('[data-module-status]')).to_have_text('Pilih setidaknya satu keputusan.')
            for checkbox in page.locator('[data-decision] [name=ids]').all():
                checkbox.check()
            held = []
            page.route("**/riwayat/hapus-massal/", lambda route: held.append(route))
            page.locator('[data-decision-bulk] button').click()
            expect(page.locator('[data-decision]:visible')).to_have_count(0)
            self.assertEqual(len(held), 1)
            held.pop().fulfill(status=403, json={"ok": False, "message": "Penghapusan gagal."})
            expect(page.locator('[data-decision]:visible')).to_have_count(2)
            expect(page.locator('[data-module-status]')).to_have_text('Penghapusan gagal.')
            page.unroute("**/riwayat/hapus-massal/")

            page.route("**/riwayat/*/ubah/", lambda route: route.fulfill(status=400, json={"ok": False, "message": "Alasan gagal."}))
            note = page.locator('[data-decision] textarea').first
            original = note.input_value()
            note.fill('Perubahan yang ditolak')
            page.locator('[data-decision-update] button').first.click()
            expect(note).to_have_value(original)
            page.unroute("**/riwayat/*/ubah/")
            page.locator('[data-decision-bulk] button').click()
            expect(page.locator('[data-module-status]')).to_have_text('2 keputusan dihapus.')
            expect(page.locator('[data-decision]')).to_have_count(0)
            self.assertEqual(page.evaluate("window.modulePage"), "same-page")

            browser.close()

    def test_ajax_crud_filters_and_pagination_without_navigation(self):
        from playwright.sync_api import expect, sync_playwright

        user = make_user()
        product = make_product(product_name="Produk browser", brand="Merek browser")
        for index in range(12):
            Decision.objects.create(user=user, product=product, note=f"Catatan {index}")
        self.client.force_login(user)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            context.add_cookies([{"name": settings.SESSION_COOKIE_NAME,
                                 "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                                 "url": self.live_server_url}])
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + "/riwayat/")
            page.evaluate("window.modulePage = 'same-page'")
            page.locator("[data-page]", has_text="Berikutnya").click()
            expect(page.locator("[data-decision]")).to_have_count(2)
            expect(page).to_have_url(re.compile(r"page=2"))
            page.locator("[data-page]", has_text="Sebelumnya").click()
            expect(page.locator("[data-decision]")).to_have_count(10)
            page.locator("[data-decision-filter] [name=q]").fill("Tidak cocok")
            expect(page.locator("[data-decision]")).to_have_count(0)
            page.locator("[data-filter-reset]").click()
            expect(page.locator("[data-decision]")).to_have_count(10)

            create = page.locator("[data-decision-create]")
            create.locator("[name=product]").select_option(str(product.pk))
            create.locator("[name=note]").fill("Keputusan browser")
            create.locator("button").click()
            row = page.locator("[data-decision]").filter(has=page.locator("textarea", has_text="Keputusan browser"))
            expect(row).to_have_count(1)
            row.locator("textarea").fill("Alasan diperbarui")
            row.locator("[data-decision-update] button").click()
            expect(page.locator("[data-module-status]")).to_have_text("Alasan disimpan.")
            row = page.locator("[data-decision]").filter(has=page.locator("textarea", has_text="Alasan diperbarui"))
            row.locator("[data-decision-delete] button").click()
            expect(page.locator("[data-module-status]")).to_have_text("Keputusan dihapus.")
            expect(page.locator("textarea", has_text="Alasan diperbarui")).to_have_count(0)
            self.assertEqual(page.evaluate("window.modulePage"), "same-page")
            self.assertEqual(errors, [])
            browser.close()

    def test_responsive_pages_and_unique_labels(self):
        from playwright.sync_api import expect, sync_playwright

        user = make_user()
        product = make_product(product_name="Produk" * 40, brand="Contoh", proteins_100g=2)
        Decision.objects.create(user=user, product=product, note="Alasan" * 80)
        Preference.objects.create(user=user, nutrient="protein", direction="max", weight=3)
        self.client.force_login(user)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context()
            context.add_cookies([{"name": settings.SESSION_COOKIE_NAME,
                                 "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                                 "url": self.live_server_url}])
            page = context.new_page()
            for width in (390, 768, 1024, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                for path in ("/preferensi/", "/riwayat/"):
                    page.goto(self.live_server_url + path)
                    page.wait_for_function("getComputedStyle(document.querySelector('.card')).borderRadius === '20px'")
                    self.assertTrue(page.locator("main [id]").evaluate_all(
                        "elements => new Set(elements.map(element => element.id)).size === elements.length"))
                    self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                    self.assertLessEqual(page.locator("main").evaluate("element => element.scrollWidth"),
                                         page.locator("main").evaluate("element => element.clientWidth"))
                    if os.getenv("PILIHYUK_SCREENSHOT_DIR"):
                        directory = Path(os.environ["PILIHYUK_SCREENSHOT_DIR"])
                        directory.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(directory / f"{path.strip('/')}-{width}.png"), full_page=True)

            browser.close()

