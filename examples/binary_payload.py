from pyais import decode

# This is a message of type 6 which contains binary payload
msg = decode(b"!AIVDM,1,1,,B,6B?n;be:cbapalgc;i6?Ow4,2*4A")

assert msg.msg_type == 6

# The payload is bytes by default
assert msg.data == b'\xeb/\x11\x8f\x7f\xf1'

# Convert the raw bytes to number
number = int.from_bytes(msg.data, byteorder="big")

assert bin(number)[2:] == "111010110010111100010001100011110111111111110001"
