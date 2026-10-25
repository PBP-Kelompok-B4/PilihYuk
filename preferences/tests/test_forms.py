from django.test import TestCase

from preferences.forms import PreferenceForm
from preferences.models import Preference
from .helpers import make_user


class PreferenceFormTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_invalid_weight_and_duplicate_have_friendly_errors(self):
        for weight in (0, 4, "1.5", "abc", ""):
            form = PreferenceForm({"nutrient": "protein", "direction": "max", "weight": weight}, user=self.user)
            self.assertFalse(form.is_valid())
            self.assertIn("weight", form.errors)
        Preference.objects.create(user=self.user, nutrient="protein", direction="max")
        form = PreferenceForm({"nutrient": "protein", "direction": "max", "weight": 2}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("sudah aktif", str(form.errors))

    def test_edit_cannot_change_nutrient_or_owner(self):
        item = Preference.objects.create(user=self.user, nutrient="protein", direction="max")
        form = PreferenceForm({"nutrient": "sugar", "direction": "min", "weight": 3, "user": 999},
                              user=self.user, instance=item)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual((saved.nutrient, saved.user, saved.direction, saved.weight), ("protein", self.user, "min", 3))
