"""Tes browser opsional: PILIHYUK_BROWSER_TESTS=1, Playwright, dan Chrome lokal."""

import importlib.util
import os
import re
from pathlib import Path
import unittest

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from preferences.models import Decision, Preference
from .helpers import make_product, make_user


@unittest.skipUnless(os.getenv("PILIHYUK_BROWSER_TESTS") == "1" and importlib.util.find_spec("playwright"),
                     "Tes browser memerlukan opt-in dan Playwright lokal.")
class DecisionBrowserTests(StaticLiveServerTestCase):
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

    def test_responsive_pages_keyboard_focus_and_failed_preference_rollback(self):
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

            page.set_viewport_size({"width": 390, "height": 900})
            page.goto(self.live_server_url + "/preferensi/")
            expect(page.locator("#direction-energy")).to_be_disabled()
            page.locator("#weight-protein-3").focus()
            page.keyboard.press("ArrowLeft")
            expect(page.locator("[data-module-status]")).to_have_text("Preferensi disimpan.")
            expect(page.locator("#weight-protein-2")).to_be_checked()
            expect(page.locator("#weight-protein-2")).to_be_focused()
            page.locator("#direction-protein").select_option("min")
            expect(page.locator('[data-nutrient="protein"]')).to_have_attribute("data-direction", "min")
            expect(page.locator('[data-nutrient="protein"] [data-preview]')).to_contain_text("1 dari 1")

            page.route("**/preferensi/*/ubah/", lambda route: route.fulfill(status=400, json={"ok": False, "message": "Simpan gagal."}))
            page.locator("label", has=page.locator("#weight-protein-1")).click()
            expect(page.locator("[data-module-status]")).to_have_text("Simpan gagal.")
            expect(page.locator("#weight-protein-2")).to_be_checked()
            expect(page.locator("#direction-protein")).to_have_value("min")
            page.unroute("**/preferensi/*/ubah/")
            page.reload()
            expect(page.locator("#weight-protein-2")).to_be_checked()
            expect(page.locator("#direction-protein")).to_have_value("min")

            page.locator("#active-protein").click()
            expect(page.locator("#active-protein")).to_have_attribute("aria-checked", "false")
            expect(page.locator("#active-protein")).to_be_focused()
            expect(page.locator("#direction-protein")).to_be_disabled()
            expect(page.locator("#weight-protein-2")).to_be_disabled()
            page.locator("#active-protein").click()
            expect(page.locator("#active-protein")).to_have_attribute("aria-checked", "true")
            expect(page.locator("#weight-protein-2")).to_be_checked()
            self.assertEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
            browser.close()
