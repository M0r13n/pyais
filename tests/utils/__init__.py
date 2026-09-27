def _twos(value: int, bits: int) -> str:
    """Render `value` as a `bits`-wide two's complement bit string."""
    if value < 0:
        value += 1 << bits
    return format(value & ((1 << bits) - 1), f'0{bits}b')


def _sixbit(text: str, chars: int) -> str:
    """Encode `text` as `chars` six-bit ASCII characters."""
    padded = text.ljust(chars, '@')[:chars]
    out = ''
    for ch in padded:
        c = ord(ch)
        out += format((c - 64) if c >= 64 else c, '06b')
    return out


def _sub_circle(lon, lat, radius, scale=0, precision=4) -> str:
    bits = _twos(0, 3) + _twos(scale, 2)
    bits += _twos(round(lon * 60000), 25) + _twos(round(lat * 60000), 24)
    bits += _twos(precision, 3) + _twos(radius, 12) + '0' * 18
    assert len(bits) == 87
    return bits


def _sub_rectangle(lon, lat, east, north, orientation, scale=0, precision=4) -> str:
    bits = _twos(1, 3) + _twos(scale, 2)
    bits += _twos(round(lon * 60000), 25) + _twos(round(lat * 60000), 24)
    bits += _twos(precision, 3) + _twos(east, 8) + _twos(north, 8)
    bits += _twos(orientation, 9) + '0' * 5
    assert len(bits) == 87
    return bits


def _sub_sector(lon, lat, radius, left, right, scale=0, precision=4) -> str:
    bits = _twos(2, 3) + _twos(scale, 2)
    bits += _twos(round(lon * 60000), 25) + _twos(round(lat * 60000), 24)
    bits += _twos(precision, 3) + _twos(radius, 12)
    bits += _twos(left, 9) + _twos(right, 9)
    assert len(bits) == 87
    return bits


def _sub_waypoints(shape, points, scale=0) -> str:
    """Polyline (shape 3) or polygon (shape 4): four (bearing, distance) pairs."""
    bits = _twos(shape, 3) + _twos(scale, 2)
    for bearing, distance in points:
        bits += _twos(bearing, 10) + _twos(distance, 10)
    bits += '00'
    assert len(bits) == 87
    return bits


def _sub_text(text) -> str:
    bits = _twos(5, 3) + _sixbit(text, 14)
    assert len(bits) == 87
    return bits


def _pack_sub_areas(bits: str) -> bytes:
    """Left-align a run of 87-bit sub-area records into whole bytes.

    87 is not a multiple of 8, so the records are padded on the right rather
    than truncated to a byte boundary.
    """
    padded = bits + '0' * (-len(bits) % 8)
    return int(padded, 2).to_bytes(len(padded) // 8, 'big')
