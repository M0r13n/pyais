from pyais.messages import NMEAMessage

message = NMEAMessage(b"!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")
print(message.decode())

# or

message = NMEAMessage.from_string("!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C")
print(message.decode())
