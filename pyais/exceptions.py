class InvalidNMEAMessageException(Exception):
    """Invalid NMEA Message"""
    pass


class InvalidChecksumException(Exception):
    """Invalid Checksum"""
    pass


class UnknownMessageException(Exception):
    """Message not supported yet"""
    pass
