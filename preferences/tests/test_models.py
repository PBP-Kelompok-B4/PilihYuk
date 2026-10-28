from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from preferences.models import Decision, Preference
from .helpers import make_product, make_shelf, make_user


class PreferenceModelTests(TestCase):
    def test_default_weight_and_unique_nutrient_per_user(self):
        user = make_user()
        preference = Preference.objects.create(user=user, nutrient="protein", direction="max")
        self.assertEqual(preference.weight, 2)
        with self.assertRaises(ValidationError):
            Preference(user=user, nutrient="protein", direction="min").full_clean()

    def test_weight_and_choices_are_validated(self):
        user = make_user()
        for fields in ({"weight": 0}, {"weight": 4}, {"nutrient": "fat"}, {"direction": "up"}):
            values = {"user": user, "nutrient": "fiber", "direction": "max", **fields}
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                Preference(**values).full_clean()

    def test_database_enforces_unique_nutrient_only_within_user(self):
        user = make_user()
        Preference.objects.create(user=user, nutrient="protein", direction="max")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Preference.objects.create(user=user, nutrient="protein", direction="min")
        other = make_user("lain")
        Preference.objects.create(user=other, nutrient="protein", direction="min")
        self.assertEqual(other.nutrition_preferences.count(), 1)

    def test_description_identifies_preference(self):
        preference = Preference(user=make_user(), nutrient="protein", direction="max")
        self.assertIn("Protein", str(preference))


class DecisionModelTests(TestCase):
    def test_history_survives_deleted_shelf_and_product(self):
        user = make_user()
        product = make_product()
        shelf = make_shelf(user)
        decision = Decision.objects.create(user=user, product=product, shelf=shelf)
        shelf.delete()
        product.delete()
        decision.refresh_from_db()
        self.assertIsNone(decision.shelf)
        self.assertIsNone(decision.product)
        self.assertIn("Tidak diketahui", str(decision))

    def test_newest_first_and_note_limit(self):
        user = make_user()
        product = make_product()
        first = Decision.objects.create(user=user, product=product)
        second = Decision.objects.create(user=user, product=product, note="Pilihan hari ini")
        self.assertEqual(list(user.decisions.all()), [second, first])
        self.assertIn("Produk contoh", str(second))
        second.note = "x" * 501
        with self.assertRaises(ValidationError):
            second.full_clean()
