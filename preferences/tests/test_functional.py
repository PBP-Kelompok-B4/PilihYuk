"""Tes browser opsional: PILIHYUK_BROWSER_TESTS=1, Playwright, dan Chrome lokal."""

import importlib.util
import os
import re
import unittest

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from preferences.models import Decision
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
