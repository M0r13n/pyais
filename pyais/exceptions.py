class InvalidNMEAMessageException(Exception):
    """Invalid NMEA Message"""
    pass


class UnknownMessageException(Exception):
    """Message not supported yet"""
    pass


class MissingMultipartMessageException(Exception):
    """Multipart message with missing parts provided"""


class TooManyMessagesException(Exception):
    """Too many messages"""
