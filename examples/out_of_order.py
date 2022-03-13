"""
The following example shows how to deal with messages that are out of order.

In many cases it is not guaranteed that the messages arrive in the correct order.
The most prominent example would be UDP. For this use case, there is the `OutOfOrderByteStream`
class. You can pass any number of messages as an iterable into this class and it will
handle the assembly of the messages.
"""
from pyais.stream import IterMessages

messages = [
    b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
    b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
    b'!AIVDM,2,2,9,A,F@V@00000000000,2*3D',
    b'!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
]

for msg in IterMessages(messages):
    print(msg.decode())
