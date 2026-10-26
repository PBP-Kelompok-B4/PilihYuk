from django.test import TestCase
from django.core.cache import cache
from django.urls import reverse

from preferences.models import Preference
from .helpers import make_user


class AuthorizationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.owner = make_user()
        self.other = make_user("lain")
        self.item = Preference.objects.create(user=self.owner, nutrient="protein", direction="max")

    def test_other_user_gets_clear_forbidden_html_and_json(self):
        self.client.force_login(self.other)
        for action in ("update", "delete"):
            url = reverse(f"preferences:preference_{action}", args=[self.item.pk])
            response = self.client.post(url)
            self.assertContains(response, "Kamu tidak punya akses ke data ini.", status_code=403)
            for headers in ({"HTTP_ACCEPT": "application/json"}, {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}):
                response = self.client.post(url, **headers)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), {"ok": False, "message": "Kamu tidak punya akses ke data ini."})

    def test_guests_redirect_and_missing_objects_are_not_found(self):
        for action in ("update", "delete"):
            url = reverse(f"preferences:preference_{action}", args=[self.item.pk])
            self.assertEqual(self.client.post(url).status_code, 302)
        self.client.force_login(self.owner)
        url = reverse("preferences:preference_delete", args=[99999])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(self.client.post(url, HTTP_ACCEPT="application/json").status_code, 404)
