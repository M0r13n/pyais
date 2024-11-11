import unittest
from pyais.constants import TurnRate, TalkerID, NavigationStatus, ManeuverIndicator, EpfdType, ShipType


class TestPyAISConstants(unittest.TestCase):

    def test_turn_rate_no_ti_default(self):
        self.assertEqual(repr(TurnRate.NO_TI_DEFAULT), "<TurnRate.NO_TI_DEFAULT: -128.0>")
        self.assertEqual(str(TurnRate.NO_TI_DEFAULT), "-128.0")

    def test_talker_id_base_station(self):
        self.assertEqual(repr(TalkerID.Base_Station), "<TalkerID.Base_Station: 'AB'>")
        self.assertEqual(str(TalkerID.Base_Station), "AB")

    def test_navigation_status_aground(self):
        self.assertEqual(repr(NavigationStatus.Aground), "<NavigationStatus.Aground: 6>")
        self.assertEqual(str(NavigationStatus.Aground), "6")

    def test_maneuver_indicator_no_special_maneuver(self):
        self.assertEqual(repr(ManeuverIndicator.NoSpecialManeuver), "<ManeuverIndicator.NoSpecialManeuver: 1>")
        self.assertEqual(str(ManeuverIndicator.NoSpecialManeuver), "1")

    def test_epfd_type_glonass(self):
        self.assertEqual(repr(EpfdType.GLONASS), "<EpfdType.GLONASS: 2>")
        self.assertEqual(str(EpfdType.GLONASS), "2")

    def test_ship_type_wig_hazardous_category_a(self):
        self.assertEqual(repr(ShipType.WIG_HazardousCategory_A), "<ShipType.WIG_HazardousCategory_A: 21>")
        self.assertEqual(str(ShipType.WIG_HazardousCategory_A), "21")


if __name__ == '__main__':
    unittest.main()
