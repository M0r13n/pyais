import unittest

from pyais.util import get_country, get_first_three_digits


class MMSICountryCodeTestCase(unittest.TestCase):

    def test_get_three_digits(self):
        self.assertEqual(get_first_three_digits(0), 0)
        self.assertEqual(get_first_three_digits(12), 12)
        self.assertEqual(get_first_three_digits(123), 123)
        self.assertEqual(get_first_three_digits(1234), 123)
        self.assertEqual(get_first_three_digits(12345), 123)
        self.assertEqual(get_first_three_digits(1234678901234456), 123)

    def test_random_ship_1(self):
        self.assertEqual(get_country(477890700), ('HK', 'Hong Kong'))

    def test_random_ship_2(self):
        self.assertEqual(get_country(477895500), ('HK', 'Hong Kong'))

    def test_random_ship_3(self):
        self.assertEqual(get_country(626280000), ('GA', 'Gabon'))

    def test_random_ship_4(self):
        self.assertEqual(get_country(259746000), ('NO', 'Norway'))

    def test_random_ship_5(self):
        self.assertEqual(get_country(228397700), ('FR', 'France'))

    def test_random_ship_6(self):
        self.assertEqual(get_country(273219340), ('RU', 'Russia'))

    def test_random_ship_7(self):
        self.assertEqual(get_country(273329390), ('RU', 'Russia'))

    def test_random_ship_8(self):
        self.assertEqual(get_country(249110000), ('MT', 'Malta'))
