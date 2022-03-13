class AISBaseException(Exception):
    """The base exception for all exceptions"""


class InvalidNMEAMessageException(AISBaseException):
    """Invalid NMEA Message"""
    pass


class UnknownMessageException(AISBaseException):
    """Message not supported yet"""
    pass


class MissingMultipartMessageException(AISBaseException):
    """Multipart message with missing parts provided"""


class TooManyMessagesException(AISBaseException):
    """Too many messages"""


class UnknownPartNoException(AISBaseException):
    """Unknown part number"""


class InvalidDataTypeException(AISBaseException):
    """An Unknown data type was passed to an encoding/decoding function"""
