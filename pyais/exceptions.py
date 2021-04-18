class InvalidNMEAMessageException(Exception):
    """Invalid NMEA Message"""
    pass


class UnknownMessageException(Exception):
    """Message not supported yet"""
    pass
