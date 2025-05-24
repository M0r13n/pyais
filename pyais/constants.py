import typing
from enum import Enum

# Keywords
UNDEFINED = 'Undefined'
RESERVED = 'Reserved'
NULL = 'N/A'
ANSI_RED = '\x1b[31m'
ANSI_RESET = '\x1b[0m'


class ReprEnum(Enum):

    def __str__(self) -> str:
        return str(self.value)


class TurnRate(float, ReprEnum):
    # Source: https://gpsd.gitlab.io/gpsd/AIVDM.html#_types_1_2_and_3_position_report_class_a
    # turning right at more than 5deg/30s (No TI available)
    NO_TI_RIGHT = 127
    # turning left at more than 5deg/30s (No TI available)
    NO_TI_LEFT = -127
    # 80 hex) indicates no turn information available (default)
    NO_TI_DEFAULT = -128


class TalkerID(str, ReprEnum):
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
    def _missing_(cls, value: typing.Any) -> str:
        return TalkerID.UNDEFINED

    @classmethod
    def from_value(cls, v: typing.Optional[typing.Any]) -> typing.Optional["TalkerID"]:
        return cls(v) if v is not None else None


class NavigationStatus(int, ReprEnum):
    UnderWayUsingEngine = 0
    AtAnchor = 1
    NotUnderCommand = 2
    RestrictedManoeuverability = 3
    ConstrainedByHerDraught = 4
    Moored = 5
    Aground = 6
    EngagedInFishing = 7
    UnderWaySailing = 8
    ReservedFutureAmendmentHSC = 9
    ReservedFutureAmendmentWIG = 10
    PowerDrivenVesselTowingAstern = 11
    PowerDrivenVesselPushingAhead = 12
    ReservedFutureUse = 13
    AISSARTActive = 14
    Undefined = 15

    @classmethod
    def _missing_(cls, value: object) -> int:
        return NavigationStatus.Undefined

    @classmethod
    def from_value(cls, v: typing.Optional[typing.Any]) -> typing.Optional["NavigationStatus"]:
        return cls(v) if v is not None else None


class ManeuverIndicator(int, ReprEnum):
    NotAvailable = 0
    NoSpecialManeuver = 1
    SpecialManeuver = 2
    UNDEFINED = 3

    @classmethod
    def _missing_(cls, value: object) -> int:
        return ManeuverIndicator.UNDEFINED

    @classmethod
    def from_value(cls, v: typing.Optional[typing.Any]) -> typing.Optional["ManeuverIndicator"]:
        return cls(v) if v is not None else None


class EpfdType(int, ReprEnum):
    Undefined = 0
    GPS = 1
    GLONASS = 2
    GPS_GLONASS = 3
    Loran_C = 4
    Chayka = 5
    IntegratedNavigationSystem = 6
    Surveyed = 7
    Galileo = 8
    Internal_GNSS = 15

    @classmethod
    def _missing_(cls, value: object) -> int:
        return EpfdType.Undefined

    @classmethod
    def from_value(cls, v: typing.Optional[typing.Any]) -> typing.Optional["EpfdType"]:
        return cls(v) if v is not None else None


class ShipType(int, ReprEnum):
    NotAvailable = 0
    # 20's
    WIG = 20
    WIG_HazardousCategory_A = 21
    WIG_HazardousCategory_B = 22
    WIG_HazardousCategory_C = 23
    WIG_HazardousCategory_D = 24
    WIG_Reserved = 25
    WIG_NoAdditionalInformation = 29
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

    @classmethod
    def from_value(cls, v: typing.Optional[typing.Any]) -> typing.Optional["ShipType"]:
        return cls(v) if v is not None else None


class DacFid(int, ReprEnum):
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

    @classmethod
    def from_value(cls, v: typing.Optional[typing.Any]) -> typing.Optional["DacFid"]:
        return cls(v) if v is not None else None


class NavAid(int, ReprEnum):
    DEFAULT = 0
    REFERENCE_POINT = 1
    RACON = 2
    FIXED = 3
    EMERGENCY_WRECK_MARKING_BUOY = 4
    LIGHT_NO_SECTORS = 5
    LIGHT_WITH_SECTORS = 6
    LEADING_LIGHT_FRONT = 7
    LEADING_LIGHT_REAR = 8
    BEACON_CARDINAL_N = 9
    BEACON_CARDINAL_E = 10
    BEACON_CARDINAL_S = 11
    BEACON_CARDINAL_W = 12
    BEACON_PORT_HAND = 13
    BEACON_STARBOARD_HAND = 14
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
    PREFERRED_CHANNEL_PORT_HAND = 26
    PREFERRED_CHANNEL_STARBOARD_HAND = 27
    ISOLATED_DANGER = 28
    SAFE_WATER = 29
    SPECIAL_MARK = 30
    LIGHT_VESSEL = 31

    @classmethod
    def _missing_(cls, value: object) -> int:
        return NavAid.DEFAULT

    @classmethod
    def from_value(cls, v: typing.Optional[typing.Any]) -> typing.Optional["NavAid"]:
        return cls(v) if v is not None else None


class TransmitMode(int, ReprEnum):
    TXA_TXB_RXA_RXB = 0  # default
    TXA_RXA_RXB = 1
    TXB_RXA_RXB = 2
    RESERVED = 3

    @classmethod
    def _missing_(cls, value: object) -> int:
        return TransmitMode.TXA_TXB_RXA_RXB

    @classmethod
    def from_value(cls, v: typing.Optional[typing.Any]) -> typing.Optional["TransmitMode"]:
        return cls(v) if v is not None else None


class StationType(int, ReprEnum):
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

    @classmethod
    def from_value(cls, v: typing.Optional[typing.Any]) -> typing.Optional["StationType"]:
        return cls(v) if v is not None else None


class StationIntervals(int, ReprEnum):
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

    @classmethod
    def from_value(cls, v: typing.Optional[typing.Any]) -> typing.Optional["StationIntervals"]:
        return cls(v) if v is not None else None


class SyncState(int, ReprEnum):
    """
    https://www.navcen.uscg.gov/?pageName=AISMessagesA#Sync
    """
    UTC_DIRECT = 0x00
    UTC_INDIRECT = 0x01
    BASE_DIRECT = 0x02
    BASE_INDIRECT = 0x03


COUNTRY_MAPPING = {
    201: ("AL", "Albania"),
    202: ("AD", "Andorra"),
    203: ("AT", "Austria"),
    204: ("PT", "Portugal"),
    205: ("BE", "Belgium"),
    206: ("BY", "Belarus"),
    207: ("BG", "Bulgaria"),
    208: ("VA", "Vatican"),
    209: ("CY", "Cyprus"),
    210: ("CY", "Cyprus"),
    211: ("DE", "Germany"),
    212: ("CY", "Cyprus"),
    213: ("GE", "Georgia"),
    214: ("MD", "Moldova"),
    215: ("MT", "Malta"),
    216: ("AM", "Armenia"),
    218: ("DE", "Germany"),
    219: ("DK", "Denmark"),
    220: ("DK", "Denmark"),
    224: ("ES", "Spain"),
    225: ("ES", "Spain"),
    226: ("FR", "France"),
    227: ("FR", "France"),
    228: ("FR", "France"),
    229: ("MT", "Malta"),
    230: ("FI", "Finland"),
    231: ("FO", "Faroe Is"),
    232: ("GB", "United Kingdom"),
    233: ("GB", "United Kingdom"),
    234: ("GB", "United Kingdom"),
    235: ("GB", "United Kingdom"),
    236: ("GI", "Gibraltar"),
    237: ("GR", "Greece"),
    238: ("HR", "Croatia"),
    239: ("GR", "Greece"),
    240: ("GR", "Greece"),
    241: ("GR", "Greece"),
    242: ("MA", "Morocco"),
    243: ("HU", "Hungary"),
    244: ("NL", "Netherlands"),
    245: ("NL", "Netherlands"),
    246: ("NL", "Netherlands"),
    247: ("IT", "Italy"),
    248: ("MT", "Malta"),
    249: ("MT", "Malta"),
    250: ("IE", "Ireland"),
    251: ("IS", "Iceland"),
    252: ("LI", "Liechtenstein"),
    253: ("LU", "Luxembourg"),
    254: ("MC", "Monaco"),
    255: ("PT", "Portugal"),
    256: ("MT", "Malta"),
    257: ("NO", "Norway"),
    258: ("NO", "Norway"),
    259: ("NO", "Norway"),
    261: ("PL", "Poland"),
    262: ("ME", "Montenegro"),
    263: ("PT", "Portugal"),
    264: ("RO", "Romania"),
    265: ("SE", "Sweden"),
    266: ("SE", "Sweden"),
    267: ("SK", "Slovakia"),
    268: ("SM", "San Marino"),
    269: ("CH", "Switzerland"),
    270: ("CZ", "Czech Republic"),
    271: ("TR", "Turkey"),
    272: ("UA", "Ukraine"),
    273: ("RU", "Russia"),
    274: ("MK", "FYR Macedonia"),
    275: ("LV", "Latvia"),
    276: ("EE", "Estonia"),
    277: ("LT", "Lithuania"),
    278: ("SI", "Slovenia"),
    279: ("RS", "Serbia"),
    301: ("AI", "Anguilla"),
    303: ("US", "USA"),
    304: ("AG", "Antigua Barbuda"),
    305: ("AG", "Antigua Barbuda"),
    306: ("CW", "Curacao"),
    307: ("AW", "Aruba"),
    308: ("BS", "Bahamas"),
    309: ("BS", "Bahamas"),
    310: ("BM", "Bermuda"),
    311: ("BS", "Bahamas"),
    312: ("BZ", "Belize"),
    314: ("BB", "Barbados"),
    316: ("CA", "Canada"),
    319: ("KY", "Cayman Is"),
    321: ("CR", "Costa Rica"),
    323: ("CU", "Cuba"),
    325: ("DM", "Dominica"),
    327: ("DO", "Dominican Rep"),
    329: ("GP", "Guadeloupe"),
    330: ("GD", "Grenada"),
    331: ("GL", "Greenland"),
    332: ("GT", "Guatemala"),
    334: ("HN", "Honduras"),
    336: ("HT", "Haiti"),
    338: ("US", "USA"),
    339: ("JM", "Jamaica"),
    341: ("KN", "St Kitts Nevis"),
    343: ("LC", "St Lucia"),
    345: ("MX", "Mexico"),
    347: ("MQ", "Martinique"),
    348: ("MS", "Montserrat"),
    350: ("NI", "Nicaragua"),
    351: ("PA", "Panama"),
    352: ("PA", "Panama"),
    353: ("PA", "Panama"),
    354: ("PA", "Panama"),
    355: ("PA", "Panama"),
    356: ("PA", "Panama"),
    357: ("PA", "Panama"),
    358: ("PR", "Puerto Rico"),
    359: ("SV", "El Salvador"),
    361: ("PM", "St Pierre Miquelon"),
    362: ("TT", "Trinidad Tobago"),
    364: ("TC", "Turks Caicos Is"),
    366: ("US", "USA"),
    367: ("US", "USA"),
    368: ("US", "USA"),
    369: ("US", "USA"),
    370: ("PA", "Panama"),
    371: ("PA", "Panama"),
    372: ("PA", "Panama"),
    373: ("PA", "Panama"),
    374: ("PA", "Panama"),
    375: ("VC", "St Vincent Grenadines"),
    376: ("VC", "St Vincent Grenadines"),
    377: ("VC", "St Vincent Grenadines"),
    378: ("VG", "British Virgin Is"),
    379: ("VI", "US Virgin Is"),
    401: ("AF", "Afghanistan"),
    403: ("SA", "Saudi Arabia"),
    405: ("BD", "Bangladesh"),
    408: ("BH", "Bahrain"),
    410: ("BT", "Bhutan"),
    412: ("CN", "China"),
    413: ("CN", "China"),
    414: ("CN", "China"),
    416: ("TW", "Taiwan"),
    417: ("LK", "Sri Lanka"),
    419: ("IN", "India"),
    422: ("IR", "Iran"),
    423: ("AZ", "Azerbaijan"),
    425: ("IQ", "Iraq"),
    428: ("IL", "Israel"),
    431: ("JP", "Japan"),
    432: ("JP", "Japan"),
    434: ("TM", "Turkmenistan"),
    436: ("KZ", "Kazakhstan"),
    437: ("UZ", "Uzbekistan"),
    438: ("JO", "Jordan"),
    440: ("KR", "Korea"),
    441: ("KR", "Korea"),
    443: ("PS", "Palestine"),
    445: ("KP", "DPR Korea"),
    447: ("KW", "Kuwait"),
    450: ("LB", "Lebanon"),
    451: ("KG", "Kyrgyz Republic"),
    453: ("MO", "Macao"),
    455: ("MV", "Maldives"),
    457: ("MN", "Mongolia"),
    459: ("NP", "Nepal"),
    461: ("OM", "Oman"),
    463: ("PK", "Pakistan"),
    466: ("QA", "Qatar"),
    468: ("SY", "Syria"),
    470: ("AE", "UAE"),
    471: ("AE", "UAE"),
    472: ("TJ", "Tajikistan"),
    473: ("YE", "Yemen"),
    475: ("YE", "Yemen"),
    477: ("HK", "Hong Kong"),
    478: ("BA", "Bosnia and Herzegovina"),
    501: ("AQ", "Antarctica"),
    503: ("AU", "Australia"),
    506: ("MM", "Myanmar"),
    508: ("BN", "Brunei"),
    510: ("FM", "Micronesia"),
    511: ("PW", "Palau"),
    512: ("NZ", "New Zealand"),
    514: ("KH", "Cambodia"),
    515: ("KH", "Cambodia"),
    516: ("CX", "Christmas Is"),
    518: ("CK", "Cook Is"),
    520: ("FJ", "Fiji"),
    523: ("CC", "Cocos Is"),
    525: ("ID", "Indonesia"),
    529: ("KI", "Kiribati"),
    531: ("LA", "Laos"),
    533: ("MY", "Malaysia"),
    536: ("MP", "N Mariana Is"),
    538: ("MH", "Marshall Is"),
    540: ("NC", "New Caledonia"),
    542: ("NU", "Niue"),
    544: ("NR", "Nauru"),
    546: ("PF", "French Polynesia"),
    548: ("PH", "Philippines"),
    553: ("PG", "Papua New Guinea"),
    555: ("PN", "Pitcairn Is"),
    557: ("SB", "Solomon Is"),
    559: ("AS", "American Samoa"),
    561: ("WS", "Samoa"),
    563: ("SG", "Singapore"),
    564: ("SG", "Singapore"),
    565: ("SG", "Singapore"),
    566: ("SG", "Singapore"),
    567: ("TH", "Thailand"),
    570: ("TO", "Tonga"),
    572: ("TV", "Tuvalu"),
    574: ("VN", "Vietnam"),
    576: ("VU", "Vanuatu"),
    577: ("VU", "Vanuatu"),
    578: ("WF", "Wallis Futuna Is"),
    601: ("ZA", "South Africa"),
    603: ("AO", "Angola"),
    605: ("DZ", "Algeria"),
    607: ("TF", "St Paul Amsterdam Is"),
    608: ("IO", "Ascension Is"),
    609: ("BI", "Burundi"),
    610: ("BJ", "Benin"),
    611: ("BW", "Botswana"),
    612: ("CF", "Cen Afr Rep"),
    613: ("CM", "Cameroon"),
    615: ("CG", "Congo"),
    616: ("KM", "Comoros"),
    617: ("CV", "Cape Verde"),
    618: ("AQ", "Antarctica"),
    619: ("CI", "Ivory Coast"),
    620: ("KM", "Comoros"),
    621: ("DJ", "Djibouti"),
    622: ("EG", "Egypt"),
    624: ("ET", "Ethiopia"),
    625: ("ER", "Eritrea"),
    626: ("GA", "Gabon"),
    627: ("GH", "Ghana"),
    629: ("GM", "Gambia"),
    630: ("GW", "Guinea-Bissau"),
    631: ("GQ", "Equ. Guinea"),
    632: ("GN", "Guinea"),
    633: ("BF", "Burkina Faso"),
    634: ("KE", "Kenya"),
    635: ("AQ", "Antarctica"),
    636: ("LR", "Liberia"),
    637: ("LR", "Liberia"),
    642: ("LY", "Libya"),
    644: ("LS", "Lesotho"),
    645: ("MU", "Mauritius"),
    647: ("MG", "Madagascar"),
    649: ("ML", "Mali"),
    650: ("MZ", "Mozambique"),
    654: ("MR", "Mauritania"),
    655: ("MW", "Malawi"),
    656: ("NE", "Niger"),
    657: ("NG", "Nigeria"),
    659: ("NA", "Namibia"),
    660: ("RE", "Reunion"),
    661: ("RW", "Rwanda"),
    662: ("SD", "Sudan"),
    663: ("SN", "Senegal"),
    664: ("SC", "Seychelles"),
    665: ("SH", "St Helena"),
    666: ("SO", "Somalia"),
    667: ("SL", "Sierra Leone"),
    668: ("ST", "Sao Tome Principe"),
    669: ("SZ", "Swaziland"),
    670: ("TD", "Chad"),
    671: ("TG", "Togo"),
    672: ("TN", "Tunisia"),
    674: ("TZ", "Tanzania"),
    675: ("UG", "Uganda"),
    676: ("CD", "DR Congo"),
    677: ("TZ", "Tanzania"),
    678: ("ZM", "Zambia"),
    679: ("ZW", "Zimbabwe"),
    701: ("AR", "Argentina"),
    710: ("BR", "Brazil"),
    720: ("BO", "Bolivia"),
    725: ("CL", "Chile"),
    730: ("CO", "Colombia"),
    735: ("EC", "Ecuador"),
    740: ("UK", "UK"),
    745: ("GF", "Guiana"),
    750: ("GY", "Guyana"),
    755: ("PY", "Paraguay"),
    760: ("PE", "Peru"),
    765: ("SR", "Suriname"),
    770: ("UY", "Uruguay"),
    775: ("VE", "Venezuela"),
}


class InlandLoadedType(int, ReprEnum):
    NotAvailable = 0
    Loaded = 1
    Unloaded = 2
    NotUsed = 3

    @classmethod
    def _missing_(cls, value: object) -> int:
        return InlandLoadedType.NotAvailable

    @classmethod
    def from_value(cls, v: typing.Optional[typing.Any]) -> typing.Optional["InlandLoadedType"]:
        return cls(v) if v is not None else None
