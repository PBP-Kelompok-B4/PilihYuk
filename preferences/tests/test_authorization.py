from django.test import Client, TestCase
from django.core.cache import cache
from django.urls import reverse

from preferences.models import Decision, Preference
from .helpers import make_product, make_user


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

    def test_all_write_endpoints_reject_requests_without_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        decision = Decision.objects.create(user=self.owner, product=make_product())
        urls = ["/preferensi/tambah/", f"/preferensi/{self.item.pk}/ubah/", f"/preferensi/{self.item.pk}/hapus/",
                "/riwayat/tambah/", f"/riwayat/{decision.pk}/ubah/", f"/riwayat/{decision.pk}/hapus/",
                "/riwayat/hapus-massal/"]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(client.post(url, HTTP_ACCEPT="application/json").status_code, 403)
