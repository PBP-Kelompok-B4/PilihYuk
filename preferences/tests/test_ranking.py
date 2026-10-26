from django.test import TestCase

from preferences.models import Preference
from preferences.ranking import order_metric_rows


class MetricOrderTests(TestCase):
    def test_weights_then_default_order_with_unknown_keys_at_end(self):
        rows = ["energy", "protein", "fat", "fiber", "sugar", "custom"]
        preferences = [Preference(nutrient="fiber", weight=3), Preference(nutrient="protein", weight=2),
                       Preference(nutrient="sugar", weight=2)]
        with self.assertNumQueries(0):
            result = order_metric_rows(preferences, rows)
        self.assertEqual(result, ["fiber", "protein", "sugar", "energy", "fat", "custom"])
        self.assertEqual(rows, ["energy", "protein", "fat", "fiber", "sugar", "custom"])
