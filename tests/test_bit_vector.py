import random
import unittest

from pyais.bit_vector import int_bit_vector, word_bit_vector


class BitVectorEqualityTestCase(unittest.TestCase):
    def test_simple_six_bit_ascii(self):
        """Ensure that for 6bit ASCII both bit vector implementations behave identically"""
        x = int_bit_vector(b"81mg=5@0GE=85<<?dPG?B<4QQ")
        y = word_bit_vector(b"81mg=5@0GE=85<<?dPG?B<4QQ")

        self.assertEqual(len(x), len(y))
        self.assertEqual(x._value, y._value)
        self.assertEqual(x.get(0, 250), y.get(0, 250))
        self.assertEqual(x.get_str(0, 250), y.get_str(0, 250))
        self.assertEqual(x.get_bytes(0, 250), y.get_bytes(0, 250))
        self.assertEqual(x.get_bool(27), y.get_bool(27))

    def test_simple_bytes(self):
        """Ensure that for random bytes both bit vector implementations behave identically"""
        x = int_bit_vector.from_bytes(b'!\x90PB\x05\x96\x8b\xe3\xd7\xab@1\xe0\x000c\xc0@\x0f\xa0\x00\x00\x00\x0cx\x00\x00\x00')
        y = word_bit_vector.from_bytes(b'!\x90PB\x05\x96\x8b\xe3\xd7\xab@1\xe0\x000c\xc0@\x0f\xa0\x00\x00\x00\x0cx\x00\x00\x00')

        self.assertEqual(len(x), len(y))
        self.assertEqual(x._value, y._value)
        self.assertEqual(x.get(0, 250), y.get(0, 250))
        self.assertEqual(x.get_str(0, 250), y.get_str(0, 250))
        self.assertEqual(x.get_bytes(0, 250), y.get_bytes(0, 250))
        self.assertEqual(x.get_bool(27), y.get_bool(27))

    def test_fuzzy_bytes(self):
        """Ensure both bit vector implementations behave identically for random bytes of arbitrary length"""
        for k in range(25):
            data = random.randbytes(k)
            x = int_bit_vector.from_bytes(data)
            y = word_bit_vector.from_bytes(data)
            length = len(x)
            self.assertEqual(len(x), len(y))
            for i in range(length):
                for width in range(-2, length - i + 6):  # negative, zero, normal, too wide
                    assert x.get(i, width) == y.get(i, width)
                    assert x.get_signed(i, width) == y.get_signed(i, width)
                    assert x.get_str(i, width) == y.get_str(i, width)
                    assert x.get_bytes(i, width) == y.get_bytes(i, width)
                    assert x.get_bool(i) == y.get_bool(i)

    def test_fuzzy_bytes_with_padding(self):
        """Ensure both bit vector implementations behave identically for random bytes of arbitrary length and padding"""
        for k in range(25):
            data = random.randbytes(k)
            pad = random.randint(0, min(k, 7))
            x = int_bit_vector(data, pad=pad)
            y = word_bit_vector(data, pad=pad)
            length = len(x)
            self.assertEqual(len(x), len(y))
            for i in range(length):
                for width in range(-2, length - i + 6):  # negative, zero, normal, too wide
                    assert x.get(i, width) == y.get(i, width)
                    assert x.get_signed(i, width) == y.get_signed(i, width)
                    assert x.get_str(i, width) == y.get_str(i, width)
                    assert x.get_bytes(i, width) == y.get_bytes(i, width)
                    assert x.get_bool(i) == y.get_bool(i)

    def test_eq(self):
        self.assertEqual(int_bit_vector(b'0', 2), int_bit_vector(b'1', 2))
        self.assertEqual(word_bit_vector(b'0', 2), word_bit_vector(b'1', 2))


if __name__ == '__main__':
    unittest.main()
