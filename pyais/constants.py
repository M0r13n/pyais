from enum import IntEnum, Enum

# Keywords
UNDEFINED = 'Undefined'
RESERVED = 'Reserved'
NULL = 'N/A'
ANSI_RED = '\x1b[31m'
ANSI_RESET = '\x1b[0m'


class TalkerID(str, Enum):
    """ Enum of all  NMEA talker IDs.
    See: https://gpsd.gitlab.io/gpsd/AIVDM.html#_talker_ids"""
    Base_Station = "AB"
    Dependent_Base_Station = "AD"
    Mobile_Station = "AI"
    Navigation_Station = "AN"
    Receiving_Station = "AR"
    Limited_Base_Station = "AS"
    Transmitting_Station = "AT"
    Repeater_Station = "AX"
    Base_Station_Deprecated = "BS"
    Physical_Shore_Station = "SA"
    UNDEFINED = "UNDEFINED"

    @classmethod
    def _missing_(cls, value: object) -> str:
        return TalkerID.UNDEFINED


class NavigationStatus(IntEnum):
    UnderWayUsingEngine = 0
    AtAnchor = 1
    NotUnderCommand = 2
    RestrictedManoeuverability = 3
    ConstrainedByHerDraught = 4
    Moored = 5
    Aground = 6
    EngagedInFishing = 7
    UnderWaySailing = 8
    AISSARTActive = 14
    Undefined = 15

    @classmethod
    def _missing_(cls, value: object) -> int:
        return NavigationStatus.Undefined


class ManeuverIndicator(IntEnum):
    NotAvailable = 0
    NoSpecialManeuver = 1
    SpecialManeuver = 2
    UNDEFINED = 3

    @classmethod
    def _missing_(cls, value: object) -> int:
        return ManeuverIndicator.UNDEFINED


class EpfdType(IntEnum):
    Undefined = 0
    GPS = 1
    GLONASS = 2
    GPS_GLONASS = 3
    Loran_C = 4
    Chayka = 5
    IntegratedNavigationSystem = 6
    Surveyed = 7
    Galileo = 8

    @classmethod
    def _missing_(cls, value: object) -> int:
        return EpfdType.Undefined


class ShipType(IntEnum):
    NotAvailable = 0
    # 20's
    WIG = 20
    WIG_HazardousCategory_A = 21
    WIG_HazardousCategory_B = 22
    WIG_HazardousCategory_C = 23
    WIG_HazardousCategory_D = 24
    WIG_Reserved = 25
    # 30's
    Fishing = 30
    Towing = 31
    Towing_LengthOver200 = 32
    DredgingOrUnderwaterOps = 33
    DivingOps = 34
    MilitaryOps = 35
    Sailing = 36
    PleasureCraft = 37
    # 40's
    HSC = 40
    HSC_HazardousCategory_A = 41
    HSC_HazardousCategory_B = 42
    HSC_HazardousCategory_C = 43
    HSC_HazardousCategory_D = 44
    HSC_Reserved = 45
    HSC_NoAdditionalInformation = 49
    # 50's
    PilotVessel = 50
    SearchAndRescueVessel = 51
    Tug = 52
    PortTender = 53
    AntiPollutionEquipment = 54
    LawEnforcement = 55
    SPARE = 56
    MedicalTransport = 58
    NonCombatShip = 59
    # 60's
    Passenger = 60
    Passenger_HazardousCategory_A = 61
    Passenger_HazardousCategory_B = 62
    Passenger_HazardousCategory_C = 63
    Passenger_HazardousCategory_D = 64
    Passenger_Reserved = 65
    Passenger_NoAdditionalInformation = 69
    # 70's
    Cargo = 70
    Cargo_HazardousCategory_A = 71
    Cargo_HazardousCategory_B = 72
    Cargo_HazardousCategory_C = 73
    Cargo_HazardousCategory_D = 74
    Cargo_Reserved = 75
    Cargo_NoAdditionalInformation = 79
    # 80's
    Tanker = 80
    Tanker_HazardousCategory_A = 81
    Tanker_HazardousCategory_B = 82
    Tanker_HazardousCategory_C = 83
    Tanker_HazardousCategory_D = 84
    Tanker_Reserved = 85
    Tanker_NoAdditionalInformation = 89
    # 90's
    OtherType = 90
    OtherType_HazardousCategory_A = 91
    OtherType_HazardousCategory_B = 92
    OtherType_HazardousCategory_C = 93
    OtherType_HazardousCategory_D = 94
    OtherType_Reserved = 95
    OtherType_NoAdditionalInformation = 99

    @classmethod
    def _missing_(cls, value: object) -> int:
        if isinstance(value, int):
            if 24 < value < 30:
                return ShipType.WIG_Reserved

            if 44 < value < 49:
                return ShipType.HSC_Reserved

            if 55 < value < 58:
                return ShipType.SPARE

            if 64 < value < 69:
                return ShipType.Passenger_Reserved

            if 74 < value < 79:
                return ShipType.Cargo_Reserved

            if 84 < value < 89:
                return ShipType.Tanker_Reserved

            if 94 < value < 99:
                return ShipType.OtherType_Reserved

        return ShipType.NotAvailable


class DacFid(IntEnum):
    DangerousCargoIndication = 13
    TidalWindow = 15
    NumPersonsOnBoard = 17
    ClearanceTimeToEnterPort = 19
    BerthingData = 21
    AreaNotice = 24
    RouteInfoAddressed = 29
    TextDescriptionAddressed = 31
    ETA = 221
    RTA = 222
    AtoN_MonitoringData_UK = 245
    AtoN_MonitoringData_ROI = 260


class NavAid(IntEnum):
    DEFAULT = 0
    REFERENCE_POINT = 1
    RACON = 2
    FIXED = 3
    FITTED = 4
    SPARE = 5
    LIGHT_NO_SECTORS = 6
    LIGHT_SECTORS = 7
    LEADING_LIGHT_FRONT = 8
    LEADING_LIGHT_REAR = 9
    BEACON_CARDINAL_N = 10
    BEACON_CARDINAL_E = 11
    BEACON_CARDINAL_S = 12
    BEACON_CARDINAL_W = 13
    BEACON_STARBOARD = 14
    BEACON_CHANNEL_PORT_HAND = 15
    BEACON_CHANNEL_STARBOARD_HAND = 16
    BEACON_ISOLATED_DANGER = 17
    BEACON_SAFE_WATER = 18
    BEACON_SPECIAL_MARK = 19
    CARDINAL_MARK_N = 20
    CARDINAL_MARK_E = 21
    CARDINAL_MARK_S = 22
    CARDINAL_MARK_W = 23
    PORT_HAND_MARK = 24
    STARBOARD_HAND_MARK = 25
    PREFERRED_HAND_PORT_HAND = 26
    PREFERRED_HAND_STARBOARD_HAND = 27
    ISOLATED_DANGER = 28
    SAFE_WATER = 29
    SPECIAL_MARK = 30
    LIGHT_VESSEL = 31

    @classmethod
    def _missing_(cls, value: object) -> int:
        return NavAid.DEFAULT


class TransmitMode(IntEnum):
    TXA_TXB_RXA_RXB = 0  # default
    TXA_RXA_RXB = 1
    TXB_RXA_RXB = 2
    RESERVED = 3

    @classmethod
    def _missing_(cls, value: object) -> int:
        return TransmitMode.TXA_TXB_RXA_RXB


class StationType(IntEnum):
    ALL = 0
    RESERVED = 1
    CLASS_B_ALL = 2
    SAR_AIRBORNE = 3
    AID_NAV = 4
    CLASS_B_SHIPBORNE = 5
    REGIONAL = 6

    @classmethod
    def _missing_(cls, value: object) -> int:
        if isinstance(value, int):
            if 6 <= value <= 9:
                return StationType.REGIONAL
            if 10 <= value <= 15:
                return StationType.RESERVED
        return StationType.ALL


class StationIntervals(IntEnum):
    AUTONOMOUS_MODE = 0
    MINUTES_10 = 1
    MINUTES_6 = 2
    MINUTES_3 = 3
    MINUTES_1 = 4
    SECONDS_30 = 5
    SECONDS_15 = 6
    SECONDS_10 = 7
    SECONDS_5 = 8
    NEXT_SHORT_REPORTER_INTERVAL = 9
    NEXT_LONGER_REPORTING_INTERVAL = 10
    RESERVED = 11

    @classmethod
    def _missing_(cls, value: object) -> int:
        return StationIntervals.RESERVED
