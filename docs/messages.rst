##################
Message interface
##################

Every `AISMessage` message has the following interface:


Get the parent NMEA message::

    ais = AISMessage()
    ais.nmea

Get message type::

    ais = AISMessage()
    ais.msg_type

Get content::

    ais = AISMessage()
    ais.content

`AISMessage.content` is a dictionary that holds all decoded fields. You can get all available fields
for every message through the `fields` attribute. All available fields are documented here: https://gpsd.gitlab.io/gpsd/AIVDM.html
