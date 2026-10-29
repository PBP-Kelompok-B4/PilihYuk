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
    def test_preview_ignores_old_response_and_recovers_from_error(self):
        from playwright.sync_api import expect, sync_playwright
        from .helpers import make_shelf

        user = make_user()
        product = make_product(product_name="Minuman oat contoh", brand="Contoh", quantity="1 L", proteins_100g=1.2,
                               fiber_100g=0, sugars_100g=4, sodium_100g=0.04, saturated_fat_100g=0.2)
        shelf = make_shelf(user, product, name="Susu untuk kopi")
        Decision.objects.create(user=user, product=product, shelf=shelf, note="Pilihan untuk kopi pagi.", compared_product_count=1)
        for key in ("protein", "fiber", "sugar", "sodium", "saturated_fat"):
            Preference.objects.create(user=user, nutrient=key, direction="max" if key in ("protein", "fiber") else "min", weight=2)
        self.client.force_login(user)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            context.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value, "url": self.live_server_url}])
            page = context.new_page()
            page.goto(self.live_server_url + "/preferensi/")
            expect(page.locator('[data-combined-preview]')).to_contain_text('1 produk dapat diperingkat')
            if os.getenv('PILIHYUK_SCREENSHOT_DIR'):
                directory = Path(os.environ['PILIHYUK_SCREENSHOT_DIR'])
                directory.mkdir(parents=True, exist_ok=True)
                page.wait_for_function("getComputedStyle(document.querySelector('.card')).borderRadius === '20px'")
                page.screenshot(path=str(directory / 'preferensi-realistic-1440.png'), full_page=True)
            held = []
            page.route('**/preferensi/pratinjau-gabungan/', lambda route: held.append(route))
            with page.expect_request('**/preferensi/pratinjau-gabungan/'):
                page.locator('label', has=page.locator('#weight-protein-3')).click()
            with page.expect_request('**/preferensi/pratinjau-gabungan/'):
                page.locator('label', has=page.locator('#weight-protein-1')).click()
            page.evaluate('true')
            self.assertEqual(len(held), 2)
            held[1].fulfill(json={"ok": True, "ranked_count": 2, "samples": [{"name": "Terbaru", "values": []}]})
            expect(page.locator('[data-combined-preview]')).to_contain_text('Terbaru')
            held[0].fulfill(json={"ok": True, "ranked_count": 1, "samples": [{"name": "Lama", "values": []}]})
            page.evaluate('true')
            expect(page.locator('[data-combined-preview]')).not_to_contain_text('Lama')
            page.unroute('**/preferensi/pratinjau-gabungan/')
            page.route('**/preferensi/pratinjau-gabungan/', lambda route: route.fulfill(status=500, body='Gagal'))
            page.locator('label', has=page.locator('#weight-protein-2')).click()
            expect(page.locator('[data-preview-retry]')).to_be_visible()
            page.unroute('**/preferensi/pratinjau-gabungan/')
            page.locator('[data-preview-retry]').click()
            expect(page.locator('[data-combined-preview]')).to_contain_text('Minuman oat contoh')
            page.goto(self.live_server_url + '/keputusan/')
            if os.getenv('PILIHYUK_SCREENSHOT_DIR'):
                page.wait_for_function("getComputedStyle(document.querySelector('.card')).borderRadius === '20px'")
                page.screenshot(path=str(directory / 'riwayat-realistic-1440.png'), full_page=True)
            browser.close()

    def test_history_read_cards_and_confirmation_dialog(self):
        from playwright.sync_api import expect, sync_playwright

        user = make_user()
        Decision.objects.create(user=user, product=make_product(), note="Catatan tersimpan", compared_product_count=2)
        self.client.force_login(user)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            context.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value, "url": self.live_server_url}])
            page = context.new_page()
            page.goto(self.live_server_url + "/keputusan/")
            expect(page.get_by_role("button", name="Catat Keputusan Baru", exact=True)).to_have_count(1)
            expect(page.locator('[data-decision] textarea')).to_have_count(0)
            page.get_by_role("button", name="Catat Keputusan Baru", exact=True).click()
            expect(page.locator('dialog[data-create-dialog]')).to_be_visible()
            page.keyboard.press("Escape")
            expect(page.get_by_role("button", name="Catat Keputusan Baru", exact=True)).to_be_focused()
            page.locator('[data-decision-delete] button').click()
            expect(page.locator('dialog[data-confirm-dialog]')).to_be_visible()
            expect(page.locator('[data-decision]')).to_have_count(1)
            page.get_by_role('button', name='Batal', exact=True).click()
            expect(page.locator('[data-decision]')).to_have_count(1)
            browser.close()

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
            page.goto(self.live_server_url + "/keputusan/")
            page.evaluate("window.modulePage = 'same-page'")
            page.locator('[data-decision-bulk] button').click()
            expect(page.locator('[data-module-status]')).to_have_text('Pilih setidaknya satu keputusan.')
            for checkbox in page.locator('[data-decision] [name=ids]').all():
                checkbox.check()
            held = []
            page.route("**/keputusan/hapus-massal/", lambda route: held.append(route))
            page.locator('[data-decision-bulk] button').click()
            page.get_by_role('button', name='Hapus', exact=True).click()
            expect(page.locator('[data-decision]:visible')).to_have_count(0)
            self.assertEqual(len(held), 1)
            held.pop().fulfill(status=403, json={"ok": False, "message": "Penghapusan gagal."})
            expect(page.locator('[data-decision]:visible')).to_have_count(2)
            expect(page.locator('[data-module-status]')).to_have_text('Penghapusan gagal.')
            page.unroute("**/keputusan/hapus-massal/")

            page.route("**/keputusan/*/ubah/", lambda route: route.fulfill(status=400, json={"ok": False, "message": "Alasan gagal."}))
            original = page.locator('[data-note-text]').first.text_content()
            page.locator('[data-decision-edit]').first.click()
            note = page.locator('[data-edit-dialog] textarea')
            note.fill('Perubahan yang ditolak')
            page.locator('[data-decision-update] button').first.click()
            expect(page.locator('[data-module-status]')).to_have_text('Alasan gagal.')
            expect(note).to_have_value('Perubahan yang ditolak')
            expect(page.locator('[data-note-text]').first).to_have_text(original)
            page.keyboard.press('Escape')
            page.unroute("**/keputusan/*/ubah/")
            page.locator('[data-decision-bulk] button').click()
            page.get_by_role('button', name='Hapus', exact=True).click()
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
            page.goto(self.live_server_url + "/keputusan/")
            page.evaluate("window.modulePage = 'same-page'")
            page.locator("[data-page]", has_text="Berikutnya").click()
            expect(page.locator("[data-decision]")).to_have_count(2)
            expect(page).to_have_url(re.compile(r"page=2"))
            page.locator("[data-page]", has_text="Sebelumnya").click()
            expect(page.locator("[data-decision]")).to_have_count(10)
            page.locator('summary', has_text='Cari dan filter tanggal').click()
            page.locator("[data-decision-filter] [name=q]").fill("Tidak cocok")
            expect(page.locator("[data-decision]")).to_have_count(0)
            page.locator("[data-filter-reset]").first.click()
            expect(page.locator("[data-decision]")).to_have_count(10)

            page.get_by_role('button', name='Catat Keputusan Baru', exact=True).click()
            create = page.locator("[data-decision-create]")
            create.locator("[name=product]").select_option(str(product.pk))
            create.locator("[name=note]").fill("Keputusan browser")
            create.locator("button").click()
            row = page.locator("[data-decision]").filter(has_text="Keputusan browser")
            expect(row).to_have_count(1)
            row.locator('[data-decision-edit]').click()
            page.locator('[data-edit-dialog] textarea').fill("Alasan diperbarui")
            page.locator("[data-decision-update] button").click()
            expect(page.locator("[data-module-status]")).to_have_text("Alasan disimpan.")
            row = page.locator("[data-decision]").filter(has_text="Alasan diperbarui")
            row.locator("[data-decision-delete] button").click()
            page.get_by_role('button', name='Hapus', exact=True).click()
            expect(page.locator("[data-module-status]")).to_have_text("Keputusan dihapus.")
            expect(page.locator("[data-note-text]", has_text="Alasan diperbarui")).to_have_count(0)
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
                for path in ("/preferensi/", "/keputusan/"):
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
