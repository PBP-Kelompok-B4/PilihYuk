from django.test import TestCase
from django.urls import reverse

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
