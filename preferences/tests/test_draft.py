import json

from django.core.cache import cache
from django.test import TestCase

from preferences.constants import NUTRIENT_FIELDS
from preferences.models import Preference
from .helpers import make_product, make_user


def draft(**active):
    return [{"nutrient": key, "active": key in active, "direction": "max" if key in ("protein", "fiber") else "min",
             "weight": active.get(key, 2)} for key in NUTRIENT_FIELDS]


class GlobalDraftTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = make_user()
        self.client.force_login(self.user)

    def test_save_applies_whole_draft_and_all_inactive_deletes_only_own_preferences(self):
        other = make_user("lain")
        Preference.objects.create(user=other, nutrient="fiber", direction="max")
        response = self.client.post("/preferensi/simpan/", json.dumps({"preferences": draft(protein=3, sugar=1)}),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)
        items = self.client.get("/preferensi/", HTTP_ACCEPT="application/json").json()["items"]
        self.assertEqual({item["nutrient"]: item["weight"] for item in items}, {"protein": 3, "sugar": 1})
        self.client.post("/preferensi/simpan/", json.dumps({"preferences": draft()}), content_type="application/json")
        self.assertEqual(self.user.nutrition_preferences.count(), 0)
        self.assertEqual(other.nutrition_preferences.count(), 1)

    def test_invalid_last_row_does_not_partially_save_and_rejects_bad_shapes(self):
        Preference.objects.create(user=self.user, nutrient="protein", direction="min", weight=1)
        rows = draft(protein=3)
        rows[-1]["weight"] = 4
        for payload in ({"preferences": rows}, {"preferences": []}, {"preferences": [{}] * 6}, [], {"preferences": draft()[:-1]}):
            response = self.client.post("/preferensi/simpan/", json.dumps(payload), content_type="application/json")
            self.assertEqual(response.status_code, 400)
        item = self.user.nutrition_preferences.get()
        self.assertEqual((item.direction, item.weight), ("min", 1))
        for key, value in (("active", 1), ("direction", []), ("weight", True), ("weight", "2")):
            rows = draft()
            rows[0][key] = value
            self.assertEqual(self.client.post("/preferensi/simpan/", json.dumps({"preferences": rows}),
                                             content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post("/preferensi/simpan/", "{", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.get("/preferensi/simpan/").status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post("/preferensi/simpan/").status_code, 302)

    def test_combined_preview_ranks_draft_without_saving_and_excludes_no_data(self):
        make_product(product_name="Nol", proteins_100g=0)
        make_product(product_name="Tinggi", proteins_100g=10)
        make_product(proteins_100g=None)
        make_product(proteins_100g=100, is_active=False)
        response = self.client.post("/preferensi/pratinjau-gabungan/", json.dumps({"preferences": draft(protein=3)}),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ranked_count"], 2)
        self.assertEqual([item["name"] for item in response.json()["samples"]], ["Tinggi", "Nol"])
        self.assertEqual(self.user.nutrition_preferences.count(), 0)
