############
Conversion
############

The following fields are directly converted to floats without **ANY** conversion:

1. Turn
2. Speed (speed over ground)
3. Longitude
4. Latitude
5. Course (Course over ground)
6. `to_bow`, `to_stern`, `to_port`, `to_starboard`
7. `ne_lon`, `ne_lat`, `sw_lon`, `sw_lat`

All of these values are native ``floats``. This means that you need to convert the value into the format of choice.

A common use case is to convert the values into strings, with fixed sized precision::

    content = decode_msg("!AIVDO,1,1,,,B>qc:003wk?8mP=18D3Q3wgTiT;T,0*13")
    print(content["speed"])                         #=> 102.30000000000001
    print(format(content["speed"], ".1f"))          #=> 102.3
    print(f"{content['speed'] :.6f}")               #=> 102.300000
