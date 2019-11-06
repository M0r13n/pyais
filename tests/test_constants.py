import unittest
from pyais.constants import NavigationStatus, ManeuverIndicator, ShipType, NavAid


class TestConstants(unittest.TestCase):
    def test_nav_status(self):
        self.assertEqual(NavigationStatus(3), NavigationStatus.RestrictedManoeuverability)
        self.assertEqual(NavigationStatus(17), NavigationStatus.Undefined)

    def test_maneuver_indication(self):
        self.assertEqual(ManeuverIndicator(0), ManeuverIndicator.NotAvailable)
        self.assertEqual(ManeuverIndicator(1), ManeuverIndicator.NoSpecialManeuver)
        self.assertEqual(ManeuverIndicator(2), ManeuverIndicator.SpecialManeuver)
        self.assertEqual(ManeuverIndicator(3), ManeuverIndicator.UNDEFINED)
        self.assertEqual(ManeuverIndicator(4), ManeuverIndicator.UNDEFINED)

    def test_ship_types(self):
        self.assertEqual(ShipType(25), ShipType.WIG_Reserved)
        self.assertEqual(ShipType(46), ShipType.HSC_Reserved)
        self.assertEqual(ShipType(57), ShipType.SPARE)
        self.assertEqual(ShipType(68), ShipType.Passenger_Reserved)
        self.assertEqual(ShipType(78), ShipType.Cargo_Reserved)
        self.assertEqual(ShipType(85), ShipType.Tanker_Reserved)
        self.assertEqual(ShipType(96), ShipType.OtherType_Reserved)
        self.assertEqual(ShipType(100), ShipType.NotAvailable)

    def test_navaid(self):
        self.assertEqual(NavAid(23), NavAid.CARDINAL_MARK_W)
        self.assertEqual(NavAid(32), NavAid.DEFAULT)
