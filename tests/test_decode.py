from pyais.encode import MessageType1


def test_decode_type_1():
    msg = MessageType1.from_bytes(b"!AIVDM,1,1,,A,15NPOOPP00o?b=bE`UNv4?w428D;,0*24")

    assert msg.msg_type == 1
    assert msg.repeat == 0
    assert msg.mmsi == 367533950
    assert msg.turn == 0
    assert msg.speed == 0