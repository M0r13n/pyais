import warnings

from pyais.messages import NMEAMessage, AISMessage
from pyais.stream import TCPStream, FileReaderStream, IterMessages
from pyais.decode import decode_msg
from pyais.encode import encode_dict, encode_payload

__license__ = 'MIT'
__version__ = '1.7.1'

__all__ = (
    'decode_msg',
    'encode_dict',
    'encode_payload',
    'NMEAMessage',
    'AISMessage',
    'TCPStream',
    'IterMessages',
    'FileReaderStream'
)

warnings.simplefilter('always', DeprecationWarning)  # turn off filter
warnings.warn(
    "Version 2.0.0 will introduce breaking changes. Either pin the version to 1.7.1 or switch to pyais==2.0.0-alpha to upgrade to the newest version.",
    category=DeprecationWarning)
warnings.simplefilter('default', DeprecationWarning)  # reset filter
