from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = "Rahasia-12345"


def register_data(**over):
    data = {
        "display_name": "Rani Ayu",
        "email": "rani@email.com",
        "password1": PASSWORD,
        "password2": PASSWORD,
        "terms": "on",
    }
    data.update(over)
    return data


def make_user(email="rani@email.com", name="Rani Ayu", **extra):
    return User.objects.create_user(username=email, email=email, password=PASSWORD, first_name=name, **extra)


class RegisterTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        r = self.client.post(reverse("accounts:register"), register_data())
        self.assertRedirects(r, reverse("home_page"))
        user = User.objects.get(email="rani@email.com")
        self.assertEqual((user.username, user.first_name), ("rani@email.com", "Rani Ayu"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_registration_never_grants_privileges(self):
        self.client.post(reverse("accounts:register"), register_data(is_staff="on", is_superuser="on"))
        user = User.objects.get(email="rani@email.com")
        self.assertFalse(user.is_staff or user.is_superuser)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        make_user()
        r = self.client.post(reverse("accounts:register"), register_data(email="RANI@email.com"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_input_is_rejected(self):
        for bad in (
            {"password1": "12345678", "password2": "12345678"},  # numeric / common
            {"password2": "lain-Lain-123"},  # mismatch
            {"terms": ""},  # terms unchecked
            {"email": "bukan-email"},
            {"display_name": ""},
        ):
            with self.subTest(bad=bad):
                r = self.client.post(reverse("accounts:register"), register_data(**bad))
                self.assertEqual(r.status_code, 200)
                self.assertFalse(User.objects.exists())

    def test_register_ignores_external_next(self):
        url = reverse("accounts:register")
        r = self.client.post(url + "?next=https://evil.example/", register_data())
        self.assertRedirects(r, reverse("home_page"))

    def test_register_follows_internal_next(self):
        url = reverse("accounts:register")
        r = self.client.post(url + "?next=/profil/", register_data())
        self.assertRedirects(r, reverse("accounts:profile"))

    def test_authenticated_user_is_redirected_away(self):
        self.client.force_login(make_user())
        for name in ("accounts:register", "accounts:login"):
            self.assertRedirects(self.client.get(reverse(name)), reverse("home_page"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.url = reverse("accounts:login")

    def login(self, **over):
        data = {"username": "rani@email.com", "password": PASSWORD}
        data.update(over)
        return self.client.post(self.url, data)

    def test_login_with_email(self):
        self.assertRedirects(self.login(), reverse("home_page"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_email_is_case_insensitive(self):
        self.assertRedirects(self.login(username="Rani@Email.com"), reverse("home_page"))

    def test_wrong_password_is_generic(self):
        wrong_pw = self.login(password="salah")
        no_user = self.login(username="tidakada@email.com")
        self.assertEqual(wrong_pw.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(wrong_pw.context["form"].errors, no_user.context["form"].errors)

    def test_next_internal_is_followed_external_is_not(self):
        r = self.client.post(self.url + "?next=/profil/", {"username": "rani@email.com", "password": PASSWORD})
        self.assertRedirects(r, reverse("accounts:profile"))
        self.client.logout()
        r = self.client.post(
            self.url, {"username": "rani@email.com", "password": PASSWORD, "next": "https://evil.example/"}
        )
        self.assertRedirects(r, reverse("home_page"))

    def test_remember_me_sets_30_day_session(self):
        self.login(remember="on")
        self.assertEqual(self.client.session.get_expiry_age(), int(timedelta(days=30).total_seconds()))

    def test_without_remember_session_ends_with_browser(self):
        self.login()
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)
        r = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(r, reverse("home_page"))
        self.assertNotIn("_auth_user_id", self.client.session)


class LockoutTests(TestCase):
    def setUp(self):
        make_user()
        make_user("budi@email.com", "Budi")
        self.url = reverse("accounts:login")

    def attempt(self, email, password):
        return self.client.post(self.url, {"username": email, "password": password})

    def test_account_is_locked_after_five_failures_even_with_right_password(self):
        for _ in range(4):
            self.assertEqual(self.attempt("rani@email.com", "salah").status_code, 200)
        self.assertEqual(self.attempt("rani@email.com", "salah").status_code, 429)  # gagal ke-5 mengunci
        r = self.attempt("rani@email.com", PASSWORD)
        self.assertEqual(r.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_lockout_ignores_email_case(self):
        for _ in range(5):
            self.attempt("RANI@email.com", "salah")
        self.assertEqual(self.attempt("rani@email.com", PASSWORD).status_code, 429)

    def test_other_accounts_are_not_locked(self):
        for _ in range(5):
            self.attempt("rani@email.com", "salah")
        self.assertRedirects(self.attempt("budi@email.com", PASSWORD), reverse("home_page"))

    def test_successful_login_resets_counter(self):
        for _ in range(4):
            self.attempt("rani@email.com", "salah")
        self.attempt("rani@email.com", PASSWORD)
        self.client.logout()
        for _ in range(4):
            self.attempt("rani@email.com", "salah")
        self.assertRedirects(self.attempt("rani@email.com", PASSWORD), reverse("home_page"))


class CsrfTests(TestCase):
    def test_post_without_token_is_forbidden(self):
        strict = Client(enforce_csrf_checks=True)
        self.assertEqual(strict.post(reverse("accounts:register"), register_data()).status_code, 403)
        self.assertEqual(strict.post(reverse("accounts:login"), {"username": "a", "password": "b"}).status_code, 403)
        self.assertFalse(User.objects.exists())


class ProfileTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("budi@email.com", "Budi")

    def test_anonymous_is_sent_to_login(self):
        url = reverse("accounts:profile")
        self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}")
        for name in ("accounts:profile_edit", "accounts:password"):  # POST-only: cukup ditolak login
            for method in (self.client.get, self.client.post):
                r = method(reverse(name))
                self.assertEqual(r.status_code, 302)
                self.assertTrue(r.url.startswith(reverse("accounts:login")))

    def test_profile_renders_for_user(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("accounts:profile"))
        self.assertContains(r, "Rani Ayu")
        self.assertContains(r, "rani@email.com")

    def test_edit_changes_only_own_account(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("accounts:profile_edit"),
            {"display_name": "Rani Baru", "email": "baru@email.com", "current_password": PASSWORD},
        )
        self.assertRedirects(r, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(
            (self.user.first_name, self.user.email, self.user.username),
            ("Rani Baru", "baru@email.com", "baru@email.com"),
        )
        self.assertEqual((self.other.first_name, self.other.email), ("Budi", "budi@email.com"))
        fresh = Client()
        fresh.post(reverse("accounts:login"), {"username": "baru@email.com", "password": PASSWORD})
        self.assertIn("_auth_user_id", fresh.session)  # email baru bisa dipakai masuk

    def test_email_change_needs_current_password(self):
        self.client.force_login(self.user)
        for pw in ("", "salah"):
            with self.subTest(pw=pw):
                r = self.client.post(
                    reverse("accounts:profile_edit"),
                    {"display_name": "Rani", "email": "baru@email.com", "current_password": pw},
                )
                self.assertEqual(r.status_code, 200)
                self.user.refresh_from_db()
                self.assertEqual((self.user.email, self.user.username), ("rani@email.com", "rani@email.com"))

    def test_name_change_needs_no_password(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse("accounts:profile_edit"), {"display_name": "Rani Baru", "email": "rani@email.com"})
        self.assertRedirects(r, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Rani Baru")

    def test_edit_rejects_taken_email(self):
        self.client.force_login(self.user)
        self.client.post(reverse("accounts:profile_edit"), {"display_name": "Rani", "email": "BUDI@email.com"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "rani@email.com")

    def test_edit_cannot_escalate_privileges(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("accounts:profile_edit"),
            {"display_name": "Rani", "email": "rani@email.com", "is_staff": "on", "is_superuser": "on"},
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff or self.user.is_superuser)

    def test_edit_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:profile_edit")).status_code, 405)

    def test_password_change_keeps_session(self):
        self.client.force_login(self.user)
        new = "Baru-Sandi-98765"
        r = self.client.post(
            reverse("accounts:password"), {"old_password": PASSWORD, "new_password1": new, "new_password2": new}
        )
        self.assertRedirects(r, reverse("accounts:profile"))
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new))

    def test_password_change_needs_old_password(self):
        self.client.force_login(self.user)
        new = "Baru-Sandi-98765"
        self.client.post(
            reverse("accounts:password"), {"old_password": "salah", "new_password1": new, "new_password2": new}
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_staff_sees_moderation_link_user_does_not(self):
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(reverse("accounts:profile")), "Moderasi Data")
        self.client.force_login(make_user("kurator@email.com", "Kurator", is_staff=True))
        self.assertContains(self.client.get(reverse("accounts:profile")), "Moderasi Data")


class HeaderTests(TestCase):
    def test_anonymous_header(self):
        r = self.client.get(reverse("home_page"))
        self.assertContains(r, "/masuk/")
        self.assertContains(r, "/daftar/")
        self.assertNotContains(r, "/keluar/")

    def test_authenticated_header_shows_display_name_not_email(self):
        self.client.force_login(make_user())
        r = self.client.get(reverse("home_page"))
        self.assertContains(r, "Rani Ayu")
        self.assertContains(r, "/keluar/")
        self.assertContains(r, "/profil/")
        self.assertNotContains(r, "rani@email.com")
