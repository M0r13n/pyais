from enum import Enum

# Keywords
UNDEFINED = 'Undefined'
RESERVED = 'Reserved'
NULL = 'N/A'
ANSI_RED = '\x1b[31m'
ANSI_RESET = '\x1b[0m'


class NavigationStatus(Enum):
    UnderWayUsingEngine = 0
    AtAnchor = 1
    NotUnderCommand = 2
    RestrictedManoeuverability = 3
    ConstrainedByHerDraught = 4
    Moored = 5
    Aground = 6
    EngagedInFishing = 7
    UnderWaySailing = 8
    Reserved = 9, 10, 11, 12, 13
    AISSARTActive = 14
    Undefined = 15


MANEUVER_INDICATOR = {
    0: 'Not available',
    1: 'No special maneuver',
    2: 'Special maneuver'
}

EPFD_TYPE = {
    0: 'Undefined',
    1: 'GPS',
    2: 'GLONASS',
    3: 'GPS/GLONASS',
    4: 'Loran-C',
    5: 'Chayka',
    6: 'Integrated navigation system',
    7: 'Surveyed',
    8: 'Galileo',
    15: 'Undefined'
}

SHIP_TYPE = {
    0: 'Not available',
    20: 'Wing in ground (WIG)',
    21: 'Wing in ground (WIG), Hazardous category A',
    22: 'Wing in ground (WIG), Hazardous category B',
    23: 'Wing in ground (WIG), Hazardous category C',
    24: 'Wing in ground (WIG), Hazardous category D',
    25: 'WIG Reserved',
    26: 'WIG Reserved',
    27: 'WIG Reserved',
    28: 'WIG Reserved',
    29: 'WIG Reserved',
    30: 'Fishing',
    31: 'Towing',
    32: 'Towing,length exceeds 200m or breadth exceeds 25m',
    33: 'Dredging or underwater ops',
    34: 'Diving ops',
    35: 'Military ops',
    36: 'Sailing',
    37: 'Pleasure Craft',
    38: 'Reserved',
    39: 'Reserved',
    40: 'High speed craft (HSC)',
    41: 'High speed craft (HSC), Hazardous category A',
    42: 'High speed craft (HSC), Hazardous category B',
    43: 'High speed craft (HSC), Hazardous category C',
    44: 'High speed craft (HSC), Hazardous category D',
    45: 'High speed craft (HSC), Reserved',
    46: 'High speed craft (HSC), Reserved',
    47: 'High speed craft (HSC), Reserved',
    48: 'High speed craft (HSC), Reserved',
    49: 'High speed craft (HSC), No additional information',
    50: 'Pilot Vessel',
    51: 'Search and Rescue vessel',
    52: 'Tug',
    53: 'Port Tender',
    54: 'Anti-pollution equipment',
    55: 'Law Enforcement',
    56: 'Spare - Local Vessel',
    57: 'Spare - Local Vessel',
    58: 'Medical Transport',
    59: 'Noncombatant ship according to RR Resolution No. 18',
    60: 'Passenger',
    61: 'Passenger, Hazardous category A',
    62: 'Passenger, Hazardous category B',
    63: 'Passenger, Hazardous category C',
    64: 'Passenger, Hazardous category D',
    65: 'Passenger, Reserved',
    66: 'Passenger, Reserved',
    67: 'Passenger, Reserved',
    68: 'Passenger, Reserved',
    69: 'Passenger, No additional information',
    70: 'Cargo',
    71: 'Cargo, Hazardous category A',
    72: 'Cargo, Hazardous category B',
    73: 'Cargo, Hazardous category C',
    74: 'Cargo, Hazardous category D',
    75: 'Cargo, Reserved',
    76: 'Cargo, Reserved',
    77: 'Cargo, Reserved',
    78: 'Cargo, Reserved',
    79: 'Cargo, No additional information',
    80: 'Tanker',
    81: 'Tanker, Hazardous category A',
    82: 'Tanker, Hazardous category B',
    83: 'Tanker, Hazardous category C',
    84: 'Tanker, Hazardous category D',
    85: 'Tanker, Reserved ',
    86: 'Tanker, Reserved ',
    87: 'Tanker, Reserved ',
    88: 'Tanker, Reserved ',
    89: 'Tanker, No additional information',
    90: 'Other Type',
    91: 'Other Type, Hazardous category A',
    92: 'Other Type, Hazardous category B',
    93: 'Other Type, Hazardous category C',
    94: 'Other Type, Hazardous category D',
    95: 'Other Type, Reserved',
    96: 'Other Type, Reserved',
    97: 'Other Type, Reserved',
    98: 'Other Type, Reserved',
    99: 'Other Type, No additional information'
}

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
