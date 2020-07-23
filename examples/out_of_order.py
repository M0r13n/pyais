from pyais.stream import OutOfOrderByteStream

messages = [
    b'!AIVDM,2,1,1,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*07',
    b'!AIVDM,2,2,1,A,F@V@00000000000,2*35',
    b'!AIVDM,2,1,9,A,538CQ>02A;h?D9QC800pu8@T>0P4l9E8L0000017Ah:;;5r50Ahm5;C0,0*0F',
    b'!AIVDM,2,2,9,A,F@V@00000000000,2*3D',
]

for msg in OutOfOrderByteStream(messages):
    print(msg.decode())
