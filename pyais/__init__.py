from pyais.messages import NMEAMessage, ANY_MESSAGE
from pyais.stream import TCPConnection, FileReaderStream, IterMessages
from pyais.encode import encode_dict, encode_msg, ais_to_nmea_0183
from pyais.decode import decode

__license__ = 'MIT'
__version__ = '2.0.0'
__author__ = 'Leon Morten Richter'


__all__ = (
    'encode_dict',
    'encode_msg',
    'ais_to_nmea_0183',
    'NMEAMessage',
    'ANY_MESSAGE',
    'TCPConnection',
    'IterMessages',
    'FileReaderStream',
    'decode',
)

warnings.simplefilter('always', DeprecationWarning)  # turn off filter
warnings.warn(
    "Version 2.0.0 will introduce breaking changes. Either pin the version to 1.7.1 or switch to pyais==2.0.0-alpha to upgrade to the newest version.",
    category=DeprecationWarning)
warnings.simplefilter('default', DeprecationWarning)  # reset filter
