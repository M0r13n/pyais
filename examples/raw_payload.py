from pyais import bit_vector
from pyais.messages import MSG_CLASS

payload = b'\x20\x6f\xab\x71\xdf\x80\x32\xe3\x6e\x78\x3d\xda\xa7\x49\x65\xf4\xca\x9f\x6b\xe7\x07'

bv = bit_vector(payload, pad=0)
ais_id = bv.get(0, 6)
msg = MSG_CLASS[ais_id].from_vector(bv)

print(msg)
