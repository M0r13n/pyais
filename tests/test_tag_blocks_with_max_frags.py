import unittest

from pyais.messages import GatehouseSentence
from pyais.stream import IterMessages, TagBlockQueue
from pyais.util import checksum, compute_checksum

# A type 5 payload (71 chars, 424 bits -> 2 fill bits), split into the
# maximum of 9 fragments allowed by IEC 61162-1.
PAYLOAD = "55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp888888888880"
CHUNKS = [PAYLOAD[i:i + 8] for i in range(0, len(PAYLOAD), 8)]
assert len(CHUNKS) == 9


def tag_block(fields: str) -> bytes:
    return b"\\" + fields.encode() + b"*" + f"{checksum(fields.encode()):02X}".encode() + b"\\"


def sentence(body: str) -> bytes:
    return f"{body}*{compute_checksum(body + '*'):02X}".encode()


def grouped_lines(header: str) -> list:
    """One NMEA 4.10 group: a Gatehouse wrapper followed by 9 AIVDM fragments.

    `header` formats the fragment count/number fields, e.g. '{cnt},{num}'.
    """
    total = 1 + len(CHUNKS)
    wrapper_tb = tag_block(f"g:1-{total}-4242,s:Station1,c:1609459199")
    lines = [wrapper_tb + sentence("$PGHP,1,2020,12,31,23,59,59,239,0,0,0,1,2C")]
    for i, chunk in enumerate(CHUNKS, start=1):
        fill = 2 if i == len(CHUNKS) else 0
        fields = header.format(cnt=len(CHUNKS), num=i)
        fragment_tb = tag_block(f"g:{i + 1}-{total}-4242")
        lines.append(fragment_tb + sentence(f"!AIVDM,{fields},7,A,{chunk},{fill}"))
    return lines


class NineFragmentGroupTestCase(unittest.TestCase):

    def test_spec_conformant_group_needs_no_frag_num_above_frag_cnt(self):
        tbq = TagBlockQueue()
        messages = list(IterMessages(grouped_lines("{cnt},{num}"), tbq=tbq))

        # The stream reassembles the 9 fragments and attaches the wrapper.
        self.assertEqual(len(messages), 1)
        self.assertTrue(messages[0].is_valid)
        self.assertEqual(messages[0].decode().msg_type, 5)
        self.assertIsInstance(messages[0].wrapper_msg, GatehouseSentence)

        # The tag block queue completes the group: wrapper + 9 fragments.
        group = tbq.get_nowait()
        self.assertEqual(len(group), 10)
        self.assertIsInstance(group[0], GatehouseSentence)
        self.assertEqual([s.frag_num for s in group[1:]], list(range(1, 10)))
        self.assertTrue(tbq.empty())

    def test_headers_with_frag_num_above_frag_cnt_are_rejected(self):
        # The pattern claimed to occur "in the wild": count 1, number 1..9.
        tbq = TagBlockQueue()
        messages = list(IterMessages(grouped_lines("1,{num}"), tbq=tbq))

        # '1,1' is a complete single sentence on its own and passes; '1,2'..'1,9'
        # are rejected, so neither the message nor the tag block group completes.
        self.assertEqual([m.payload for m in messages], [CHUNKS[0].encode()])
        self.assertTrue(tbq.empty())


if __name__ == "__main__":
    unittest.main()
