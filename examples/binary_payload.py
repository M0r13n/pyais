import bitarray

from pyais import decode
from pyais.util import bits2bytes, bytes2bits

# This is a message of type 6 which contains binary payload
msg = decode(b"!AIVDM,1,1,,B,6B?n;be:cbapalgc;i6?Ow4,2*4A")

assert msg.msg_type == 6

# The payload is bytes by default
assert msg.data == b'\xeb/\x11\x8f\x7f\xf1'


# But using `bytes2bits` you can convert the bytes into a bitarray
assert bytes2bits(msg.data) == bitarray.bitarray('111010110010111100010001100011110111111111110001')

#  Or to a bitstring using the bitarray to01() method
assert bytes2bits(msg.data).to01() == '111010110010111100010001100011110111111111110001'

# It is also possible to transform a set of bits back to bytes
assert bits2bytes('111010110010111100010001100011110111111111110001') == b'\xeb/\x11\x8f\x7f\xf1'
