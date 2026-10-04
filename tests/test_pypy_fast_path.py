import pathlib
import unittest

from pyais.bit_vector import int_bit_vector, word_bit_vector
from pyais.messages import MSG_CLASS
from pyais.stream import FileReaderStream


SAMPLE = pathlib.Path(__file__).parent.joinpath('nmea-sample')


class FastPathTestCase(unittest.TestCase):

    def test_real_messages_match_generic_decoder(self):
        cnt = 0
        for msg in FileReaderStream(SAMPLE):
            if msg.ais_id in (1, 2, 3) and len(msg.bv) == 168:
                cls = MSG_CLASS[msg.ais_id]
                x = cls._fast_path(int_bit_vector(msg.payload, msg.fill_bits)).asdict()
                y = cls._fast_path_pypy(word_bit_vector(msg.payload, msg.fill_bits)).asdict()
                self.assertEqual(x, y)
                self.assertEqual(
                    [(k, type(v)) for k, v in x.items()],
                    [(k, type(v)) for k, v in y.items()]
                )
                cnt += 1

        self.assertGreater(cnt, 70000)


if __name__ == '__main__':
    unittest.main()
