class AISBaseException(Exception):
    """The base exception for all exceptions"""


class InvalidNMEAMessageException(AISBaseException):
    """Invalid NMEA Message"""
    pass


class InvalidNMEAChecksum(AISBaseException):
    """Invalid Checksum for the NMEA message"""


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


class NonPrintableCharacterException(AISBaseException):
    """A non printable ASCII character (0x20 (space) to 0x7e (~)) can not be decoded"""


class TagBlockNotInitializedException(Exception):
    """The TagBlock is not initialized"""


class MissingPayloadException(AISBaseException):
    """Valid NMEA Message without payload"""
    pass
