import json

from django.core.cache import cache
from django.test import TestCase

from preferences.constants import NUTRIENT_FIELDS
from preferences.models import Preference
from .helpers import make_user


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
