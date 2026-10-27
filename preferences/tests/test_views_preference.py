import re

from django.test import TestCase
from django.core.cache import cache
from django.urls import reverse

from preferences.models import Preference
from .helpers import make_product, make_user


class PreferenceViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = make_user()
        self.url = "/preferensi/"

    def test_guest_redirect_and_owner_can_activate_and_reload(self):
        self.assertRedirects(self.client.get(self.url), "/masuk/?next=/preferensi/")
        self.client.force_login(self.user)
        self.assertContains(self.client.get(self.url), "Protein")
        result = self.client.post(reverse("preferences:preference_create"), {
            "nutrient": "protein", "direction": "max", "weight": 2,
        })
        self.assertRedirects(result, self.url)
        response = self.client.get(self.url)
        row = next(row for row in response.context["rows"] if row["nutrient"] == "protein")
        self.assertEqual((row["direction"], row["weight"], row["active"]), ("max", 2, True))

    def test_owner_updates_deletes_and_rejects_invalid_input(self):
        self.client.force_login(self.user)
        item = Preference.objects.create(user=self.user, nutrient="protein", direction="max")
        update = reverse("preferences:preference_update", args=[item.pk])
        delete = reverse("preferences:preference_delete", args=[item.pk])
        self.assertEqual(self.client.post(update, {"direction": "min", "weight": 3}).status_code, 302)
        row = self.client.get(self.url).context["rows"][0]
        self.assertEqual((row["weight"], row["direction"]), (3, "min"))
        self.assertEqual(self.client.post(update, {"direction": "max", "weight": "abc"}).status_code, 400)
        row = self.client.get(self.url).context["rows"][0]
        self.assertEqual((row["weight"], row["direction"]), (3, "min"))
        self.assertEqual(self.client.post(delete).status_code, 302)
        self.assertFalse(self.client.get(self.url).context["rows"][0]["active"])

    def test_inactive_controls_disabled_and_wrong_methods_rejected(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "<fieldset disabled", count=12)
        self.assertEqual(self.client.get(reverse("preferences:preference_create")).status_code, 405)
        self.assertEqual(self.client.post(self.url).status_code, 405)
        self.assertEqual(self.client.post(reverse("preferences:preference_create"), {}).status_code, 400)

    def test_nutrient_rows_show_distinct_decorative_icons_and_keep_text_labels(self):
        self.client.force_login(self.user)
        html = self.client.get(self.url).content.decode()
        expected = (
            ("protein", "Protein", "beef"), ("fiber", "Serat", "wheat"),
            ("sugar", "Gula", "candy"), ("sodium", "Natrium", "droplets"),
            ("saturated_fat", "Lemak jenuh", "droplet"), ("energy", "Kalori", "flame"),
        )
        for nutrient, label, icon in expected:
            with self.subTest(nutrient=nutrient):
                heading = re.search(r'data-nutrient="' + nutrient + r'"[^>]*>\s*<h3\b[^>]*>(.*?)</h3>', html, re.S)
                self.assertIsNotNone(heading)
                self.assertIn(label, heading.group(1))
                self.assertRegex(heading.group(1), r'<svg\b[^>]*class="[^"]*\blucide-' + icon + r'\b')
                self.assertIn('aria-hidden="true"', heading.group(1))
                self.assertIn('focusable="false"', heading.group(1))
                self.assertNotIn('<img', heading.group(1))

    def test_list_contains_only_current_users_preferences(self):
        Preference.objects.create(user=self.user, nutrient="protein", direction="max", weight=3)
        other = make_user("lain")
        self.client.force_login(other)
        self.assertTrue(all(not row["active"] for row in self.client.get(self.url).context["rows"]))

    def test_preview_counts_known_active_values_and_scales_sodium(self):
        self.client.force_login(self.user)
        make_product(product_name="Nol", sodium_100g=0)
        make_product(product_name="Ada", sodium_100g=0.1234)
        make_product(sodium_100g=None)
        make_product(sodium_100g=9, is_active=False)
        response = self.client.get("/preferensi/pratinjau/", {"nutrient": "sodium", "direction": "min"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True, "ranked_count": 2, "total_active": 3,
                         "samples": [{"name": "Nol", "value": 0.0, "unit": "mg"},
                                     {"name": "Ada", "value": 123.4, "unit": "mg"}]})

    def test_json_crud_and_validation_envelope(self):
        self.client.force_login(self.user)
        headers = {"HTTP_ACCEPT": "application/json"}
        result = self.client.post(reverse("preferences:preference_create"),
                                  {"nutrient": "fiber", "direction": "max", "weight": 2}, **headers)
        self.assertEqual(result.status_code, 201)
        item = result.json()["item"]
        self.assertEqual(item, {"id": item["id"], "nutrient": "fiber", "nutrient_label": "Serat", "direction": "max", "weight": 2})
        self.assertEqual(self.client.get(self.url, **headers).json()["items"], [item])
        url = reverse("preferences:preference_update", args=[item["id"]])
        updated = self.client.post(url, {"direction": "min", "weight": 3}, **headers)
        self.assertEqual(updated.json()["item"]["direction"], "min")
        invalid = self.client.post(url, {"direction": "max", "weight": 4}, **headers)
        self.assertEqual(invalid.status_code, 400)
        self.assertFalse(invalid.json()["ok"])
        self.assertIn("weight", invalid.json()["errors"])
        result = self.client.post(reverse("preferences:preference_delete", args=[item["id"]]), **headers)
        self.assertTrue(result.json()["ok"])
        self.assertEqual(self.client.get(self.url, **headers).json()["items"], [])

    def test_preview_max_limit_errors_methods_and_guests(self):
        url = "/preferensi/pratinjau/"
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        for value in (1, 3, 2, 4):
            make_product(product_name=str(value), proteins_100g=value)
        result = self.client.get(url, {"nutrient": "protein", "direction": "max"}).json()
        self.assertEqual([item["value"] for item in result["samples"]], [4.0, 3.0, 2.0])
        for params in ({}, {"nutrient": "invalid", "direction": "max"}, {"nutrient": "protein", "direction": "invalid"}):
            response = self.client.get(url, params)
            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.json()["ok"])
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertFalse(self.client.get(reverse("preferences:preference_create"), HTTP_ACCEPT="application/json").json()["ok"])
