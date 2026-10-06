import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from product_catalog import open_food_facts as off


class NormalizeBarcodeTests(SimpleTestCase):
    def test_matches_open_food_facts_rules(self):
        cases = {
            "089686010947": "0089686010947",  # UPC 12 digit diberi 0 di depan
            "0089686010947": "0089686010947",
            "0000000000017": "00000017",  # menjadi EAN-8
            "17": "00000017",
            "96385074": "96385074",
            "0000096385074": "96385074",
            "034000470693": "0034000470693",
            "123456789": "0000123456789",
            "3017620422003": "3017620422003",
            "03017620422003": "3017620422003",  # 14 digit diawali 0
            "13017620422000": "13017620422000",
            " 3017-6204 22003 ": "3017620422003",  # selain digit dibuang
            "": "",
            "abc": "",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(off.normalize_barcode(raw), expected)
        self.assertIsNone(off.normalize_barcode(None))


class IsSoldInIndonesiaTests(SimpleTestCase):
    def test_only_list_with_indonesia_counts(self):
        self.assertTrue(off.is_sold_in_indonesia({"countries_tags": ["en:france", "en:indonesia"]}))
        self.assertFalse(off.is_sold_in_indonesia({"countries_tags": ["en:france"]}))
        self.assertFalse(off.is_sold_in_indonesia({"countries_tags": []}))
        self.assertFalse(off.is_sold_in_indonesia({"countries_tags": "en:indonesia"}))
        self.assertFalse(off.is_sold_in_indonesia({}))
        self.assertFalse(off.is_sold_in_indonesia(None))


class HasValueTests(SimpleTestCase):
    def test_open_food_facts_empty_markers(self):
        product = {"grade": "b", "unknown": "unknown", "na": "not-applicable", "blank": " ", "tags": []}
        self.assertTrue(off.has_value(product, "grade"))
        for field in ["unknown", "na", "blank", "tags", "missing"]:
            with self.subTest(field=field):
                self.assertFalse(off.has_value(product, field))


class ReadCsvTests(SimpleTestCase):
    def test_keeps_only_indonesian_rows_shaped_like_api(self):
        header = "code\tproduct_name\tcountries_tags\tnutriscore_grade\tnova_group\tsugars_100g\tlabels_tags"
        rows = [
            "089686010947\tMi Goreng\ten:france,en:indonesia\tc\t4.0\t7\ten:halal",
            "3017620422003\tNutella\ten:france\te\t4\t56.3\t",
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "products.csv"
            path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
            products = list(off.read_indonesian_products_from_csv(str(path)))

        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["code"], "089686010947")
        self.assertEqual(product["countries_tags"], ["en:france", "en:indonesia"])
        self.assertEqual(product["labels_tags"], ["en:halal"])
        self.assertEqual(product["nutrition_grades"], "c")
        self.assertEqual(product["nova_group"], 4)
        self.assertEqual(product["nutriments"], {"sugars_100g": 7.0})


class GetJsonTests(SimpleTestCase):
    @mock.patch("product_catalog.open_food_facts.time.sleep")
    @mock.patch("product_catalog.open_food_facts.requests.get")
    def test_retries_on_503_then_returns_json(self, fake_get, fake_sleep):
        busy = mock.Mock(status_code=503)
        ok = mock.Mock(status_code=200)
        ok.json.return_value = {"product": {"code": "17"}}
        fake_get.side_effect = [busy, ok]

        self.assertEqual(off.get_json("https://example.test", retry_waits=(2,)), {"product": {"code": "17"}})
        fake_sleep.assert_called_once_with(2)
