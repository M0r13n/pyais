"""
The following example shows how you can get the communication state
of a message. This works for message types 1, 2, 4, 9, 11 and 18.

These messages contain diagnostic information for the radio system.
"""
from pyais import decode
import json
import functools

msg = '!AIVDM,1,1,,A,B69Gk3h071tpI02lT2ek?wg61P06,0*1F'
decoded = decode(msg)

print("The raw radio value is:", decoded.radio)
print("Communication state is SOTMDA:", decoded.is_sotdma)
print("Communication state is ITDMA:", decoded.is_itdma)

pretty_json = functools.partial(json.dumps, indent=4)
print("Communication state:", pretty_json(decoded.get_communication_state()))
