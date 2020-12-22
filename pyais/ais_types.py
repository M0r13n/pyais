from enum import IntEnum


class AISType(IntEnum):
    # Refer to https://gpsd.gitlab.io/gpsd/AIVDM.html
    NOT_IMPLEMENTED = 0
    POS_CLASS_A1 = 1
    POS_CLASS_A2 = 2
    POS_CLASS_A3 = 3
    BASE_STATION = 4
    STATIC_AND_VOYAGE = 5
    BINARY_ADDRESSED = 6
    BINARY_ACK = 7
    BINARY_BROADCAST = 8
    SAR_AIRCRAFT_POS = 9
    DATE_INQ = 10
    DATE_RESP = 11
    SAFETY_MSG = 12
    SAFETY_ACK = 13
    SAFETY_BROADCAST = 14
    INTERROGATE = 15
    ASSIGN_MODE = 16
    DGNSS = 17
    POS_CLASS_B = 18
    POS_CLASS_B_EXT = 19
    LINK_MGMT = 20
    AID_TO_NAV = 21
    CHANNEL_MGMT = 22
    GROUP_ASSIGN = 23
    STATIC = 24
    BINARY_SINGLE_SLOT = 25
    BINARY_MULTI_SLOT = 26
    LONG_RANGE_BROADCAST = 27

    @classmethod
    def _missing_(cls, value: object) -> int:
        return AISType.NOT_IMPLEMENTED
