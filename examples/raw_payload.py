import bitarray

from pyais.messages import MSG_CLASS
from pyais.util import get_int

payload = b'\x20\x6f\xab\x71\xdf\x80\x32\xe3\x6e\x78\x3d\xda\xa7\x49\x65\xf4\xca\x9f\x6b\xe7\x07'
fill_bits = 0

bit_array = bitarray.bitarray()
bit_array.frombytes(payload)

ais_id: int = get_int(bit_array, 0, 6)
msg = MSG_CLASS[ais_id].from_bitarray(bit_array)

print(msg)
