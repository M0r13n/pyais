from enum import Enum, IntEnum

# Keywords
UNDEFINED = 'ndefined'
RESERVED = 'Reserved'
NULL = 'N/A'
ANSI_RED = '\x1b[31m'
ANSI_RESET = '\x1b[0m'


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
    def _missing_(cls, value):
        return NavigationStatus.Undefined


class ManeuverIndicator(IntEnum):
    NotAvailable = 0
    NoSpecialManeuver = 1
    SpecialManeuver = 2


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
    def _missing_(cls, value):
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
    Trug = 52
    PortTender = 53
    AntiPollutionEquipment = 54
    LawEnforcement = 55
    Spare_LocalVessel = 56
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
    def _missing_(cls, value):
        if 24 < value < 30:
            return ShipType.WIG_Reserved

        if 44 < value < 49:
            return ShipType.HSC_Reserved

        if 55 < value < 58:
            return ShipType.Spare

        if 64 < value < 69:
            return ShipType.Passenger_Reserved

        if 74 < value < 79:
            return ShipType.Cargo_Reserved

        if 84 < value < 89:
            return ShipType.Tanker_Reserved

        if 94 < value < 99:
            return ShipType.OtherType_Reserved

        return ShipType.NotAvailable


DAC_FID = {
    '1-12': 'Dangerous cargo indication',
    '1-14': 'Tidal window',
    '1-16': 'Number of persons on board',
    '1-18': 'Clearance time to enter port',
    '1-20': 'Berthing data (addressed)',
    '1-23': 'Area notice (addressed)',
    '1-25': 'Dangerous Cargo indication',
    '1-28': 'Route info addressed',
    '1-30': 'Text description addressed',
    '1-32': 'Tidal Window',
    '200-21': 'ETA at lock/bridge/terminal',
    '200-22': 'RTA at lock/bridge/terminal',
    '200-55': 'Number of persons on board',
    '235-10': 'AtoN monitoring data (UK)',
    '250-10': 'AtoN monitoring data (ROI)',
}
