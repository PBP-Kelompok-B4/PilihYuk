from django.test import TestCase
from django.urls import reverse

from preferences.models import Preference
from .helpers import make_user


class PreferenceViewTests(TestCase):
    def setUp(self):
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
        self.assertContains(response, "<fieldset disabled", count=6)
        self.assertEqual(self.client.get(reverse("preferences:preference_create")).status_code, 405)
        self.assertEqual(self.client.post(self.url).status_code, 405)
        self.assertEqual(self.client.post(reverse("preferences:preference_create"), {}).status_code, 400)

    def test_list_contains_only_current_users_preferences(self):
        Preference.objects.create(user=self.user, nutrient="protein", direction="max", weight=3)
        other = make_user("lain")
        self.client.force_login(other)
        self.assertTrue(all(not row["active"] for row in self.client.get(self.url).context["rows"]))
