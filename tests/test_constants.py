import unittest

from pyais import decode, encode_msg
from pyais.constants import NavigationStatus, ManeuverIndicator, ShipType, NavAid, TransmitMode, StationIntervals, \
    StationType


class TestConstants(unittest.TestCase):
    def test_that_nav_data_values_are_kept_for_all_values(self):
        # See: https://github.com/M0r13n/pyais/issues/123
        orignal = decode(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")

        for i in range(15):
            orignal.status = i
            encoded = encode_msg(orignal)
            decoded = decode(encoded[0])

            self.assertEqual(decoded.status.value, i)

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
        self.assertEqual(NavAid.DEFAULT, 0)
        self.assertEqual(NavAid.REFERENCE_POINT, 1)
        self.assertEqual(NavAid.RACON, 2)
        self.assertEqual(NavAid.FIXED, 3)
        self.assertEqual(NavAid.EMERGENCY_WRECK_MARKING_BUOY, 4)
        self.assertEqual(NavAid.LIGHT_NO_SECTORS, 5)
        self.assertEqual(NavAid.LIGHT_WITH_SECTORS, 6)
        self.assertEqual(NavAid.LEADING_LIGHT_FRONT, 7)
        self.assertEqual(NavAid.LEADING_LIGHT_REAR, 8)
        self.assertEqual(NavAid.BEACON_CARDINAL_N, 9)
        self.assertEqual(NavAid.BEACON_CARDINAL_E, 10)
        self.assertEqual(NavAid.BEACON_CARDINAL_S, 11)
        self.assertEqual(NavAid.BEACON_CARDINAL_W, 12)
        self.assertEqual(NavAid.BEACON_PORT_HAND, 13)
        self.assertEqual(NavAid.BEACON_STARBOARD_HAND, 14)
        self.assertEqual(NavAid.BEACON_CHANNEL_PORT_HAND, 15)
        self.assertEqual(NavAid.BEACON_CHANNEL_STARBOARD_HAND, 16)
        self.assertEqual(NavAid.BEACON_ISOLATED_DANGER, 17)
        self.assertEqual(NavAid.BEACON_SAFE_WATER, 18)
        self.assertEqual(NavAid.BEACON_SPECIAL_MARK, 19)
        self.assertEqual(NavAid.CARDINAL_MARK_N, 20)
        self.assertEqual(NavAid.CARDINAL_MARK_E, 21)
        self.assertEqual(NavAid.CARDINAL_MARK_S, 22)
        self.assertEqual(NavAid.CARDINAL_MARK_W, 23)
        self.assertEqual(NavAid.PORT_HAND_MARK, 24)
        self.assertEqual(NavAid.STARBOARD_HAND_MARK, 25)
        self.assertEqual(NavAid.PREFERRED_CHANNEL_PORT_HAND, 26)
        self.assertEqual(NavAid.PREFERRED_CHANNEL_STARBOARD_HAND, 27)
        self.assertEqual(NavAid.ISOLATED_DANGER, 28)
        self.assertEqual(NavAid.SAFE_WATER, 29)
        self.assertEqual(NavAid.SPECIAL_MARK, 30)
        self.assertEqual(NavAid.LIGHT_VESSEL, 31)

    def test_t_mode(self):
        self.assertEqual(TransmitMode(0), TransmitMode.TXA_TXB_RXA_RXB)
        self.assertEqual(TransmitMode(10), TransmitMode.TXA_TXB_RXA_RXB)

    def test_station_types(self):
        self.assertEqual(StationType(0), StationType.ALL)
        self.assertEqual(StationType(11), StationType.RESERVED)
        self.assertEqual(StationType(7), StationType.REGIONAL)
        self.assertEqual(StationType(16), StationType.ALL)

    def test_station_intervals(self):
        self.assertEqual(StationIntervals(0), StationIntervals.AUTONOMOUS_MODE)
        self.assertEqual(StationIntervals(11), StationIntervals.RESERVED)
        self.assertEqual(StationIntervals(7), StationIntervals.SECONDS_10)
        self.assertEqual(StationIntervals(12), StationIntervals.RESERVED)
