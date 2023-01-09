"""AIS tracking functionality.The AISTracker maintains as collections
of known tracks and maintains the state of each vessel. This is
necessary because several messages can give different information
about a ship. In addition, the data changes constantly (position, speed).
Each track (or vessel) is solely identified by its MMSI.
"""
import typing
import time
import dataclasses
from pyais.messages import ANY_MESSAGE, AISSentence


def now() -> float:
    """Current time as UNIX time (milliseconds)"""
    return time.time()


@dataclasses.dataclass(eq=True, order=True, slots=True)
class AISTrack:
    """Each track holds some consolidated information about a vessel.
    Each vessel is uniquely identified by its MMSI. Tracks typically hold
    information from multiple messages that were received."""
    mmsi: int = dataclasses.field(compare=True)
    turn: typing.Optional[float] = dataclasses.field(compare=False, default=None)
    speed: typing.Optional[float] = dataclasses.field(compare=False, default=None)
    lon: typing.Optional[float] = dataclasses.field(compare=False, default=None)
    lat: typing.Optional[float] = dataclasses.field(compare=False, default=None)
    course: typing.Optional[float] = dataclasses.field(compare=False, default=None)
    heading: typing.Optional[int] = dataclasses.field(compare=False, default=None)
    imo: typing.Optional[int] = dataclasses.field(compare=False, default=None)
    callsign: typing.Optional[str] = dataclasses.field(compare=False, default=None)
    shipname: typing.Optional[str] = dataclasses.field(compare=False, default=None)
    ship_type: typing.Optional[int] = dataclasses.field(compare=False, default=None)
    to_bow: typing.Optional[int] = dataclasses.field(compare=False, default=None)
    to_stern: typing.Optional[int] = dataclasses.field(compare=False, default=None)
    to_port: typing.Optional[int] = dataclasses.field(compare=False, default=None)
    to_starboard: typing.Optional[int] = dataclasses.field(compare=False, default=None)
    destination: typing.Optional[str] = dataclasses.field(compare=False, default=None)
    last_updated: float = dataclasses.field(compare=False, default_factory=now)


# compute a set of all fields only once
FIELDS = dataclasses.fields(AISTrack)


def msg_to_track(msg: ANY_MESSAGE, ts_epoch_ms: typing.Optional[float] = None) -> AISTrack:
    """Convert a AIS message into a AISTrack.
    Only fields known to class AISTrack are considered.
    Depending on the type of the message, the implementation varies.
    ts_epoch_ms can be used as a timestamp for when the message was initially received.
    :param msg:         any decoded AIS message of type AISMessage.
    :param ts_epoch_ms: optional timestamp for the message. If None (default) current time is used."""
    if ts_epoch_ms is None:
        track = AISTrack(mmsi=msg.mmsi)
    else:
        track = AISTrack(mmsi=msg.mmsi, last_updated=ts_epoch_ms)

    for field in FIELDS:
        if not hasattr(msg, field.name):
            continue
        val = getattr(msg, field.name)
        if val is not None:
            setattr(track, field.name, val)

    return track


def update_track(old: AISTrack, new: AISTrack) -> AISTrack:
    """Updates all fields of old with the values of new.
    :param old: the old AISTrack to update.
    :param new: the new AISTrack to update old with."""
    for field in FIELDS:
        new_val = getattr(new, field.name)
        if new_val is not None:
            setattr(old, field.name, new_val)
    return old


class AISTracker:
    """
    An AIS tracker receives AIS messages and maintains a collection of known tracks.
    Everything is stored in memory.
    Messages are cleaned up regularly, if they expire (receive timestamp older than threshold).
    Set ttl_in_seconds to None to never clean up.
    Unlike most other trackers, this class handles out of order reception of messages.
    This means that it is possible to pass messages to update() whose timestamp is
    older that of the message before. The latter is useful when working with multiple stations
    and/or different kinds of metadata.
    """

    def __init__(self, ttl_in_seconds: typing.Optional[int] = 600) -> None:
        """Creates a new tracker instance.
        :param ttl_in_seconds: the ttl in seconds before expired tracks are pruned."""
        self._tracks: typing.Dict[int, AISTrack] = {}  # { mmsi: AISTrack(), ...}
        self.ttl_in_seconds: typing.Optional[int] = ttl_in_seconds  # in seconds or None
        self.oldest_timestamp: typing.Optional[float] = None

    def __enter__(self) -> "AISTracker":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        return None

    def __set_oldest_timestamp(self, ts: float) -> None:
        if self.oldest_timestamp is None:
            self.oldest_timestamp = ts
        else:
            self.oldest_timestamp = min(self.oldest_timestamp, ts)

    @property
    def tracks(self) -> typing.List[AISTrack]:
        """Returns a list of all known tracks."""
        return list(self._tracks.values())

    def update(self, msg: AISSentence, ts_epoch_ms: typing.Optional[float] = None) -> None:
        """Updates a track. If the track does not yet exist, a new track is created.
        :param msg: the message to add to the track.
        :param ts_epoch_ms: an optional timestamp to tell when the message was originally received."""
        decoded = msg.decode()
        mmsi = int(decoded.mmsi)
        track = msg_to_track(decoded, ts_epoch_ms)
        self.insert_or_update(mmsi, track)
        self.cleanup()

    def get_track(self, mmsi: typing.Union[str, int]) -> typing.Optional[AISTrack]:
        """Get a track by mmsi. Returns None if the track does not exist."""
        try:
            return self._tracks[int(mmsi)]
        except KeyError:
            return None

    def pop_track(self, mmsi: typing.Union[str, int]) -> typing.Optional[AISTrack]:
        """Pop a track by mmsi. Returns the track and deletes it, if it exist. Otherwise returns None."""
        try:
            mmsi = int(mmsi)
            track = self._tracks[mmsi]
            del self._tracks[mmsi]
            return track
        except KeyError:
            return None

    def n_latest_tracks(self, n: int) -> typing.List[AISTrack]:
        """Return the latest N tracks. These are the tracks with the youngest timestamps.
        E.g. the tracks that were updated most recently."""
        n_latest = []
        n = min(n, len(self._tracks))
        tracks = sorted(self._tracks.values(), key=lambda track: track.last_updated)
        for i, track in enumerate(reversed(tracks)):
            if n <= i:
                break
            n_latest.append(track)

        return n_latest

    def insert_or_update(self, mmsi: int, track: AISTrack) -> None:
        """Insert or update a track."""
        # Does the track already exist?
        if mmsi in self._tracks:
            self.update_track(mmsi, track)
        else:
            self.insert_track(mmsi, track)
        self.__set_oldest_timestamp(track.last_updated)

    def insert_track(self, mmsi: int, new: AISTrack) -> None:
        """Creates a new track records in memory"""
        self._tracks[mmsi] = new

    def update_track(self, mmsi: int, new: AISTrack) -> None:
        """Updates an existing track in memory"""
        old = self._tracks[mmsi]
        if new.last_updated < old.last_updated:
            raise ValueError('cannot update track with older message')
        updated = update_track(old, new)
        self._tracks[mmsi] = updated

    def cleanup(self) -> None:
        """Delete all records whose last update is older than ttl."""
        if self.ttl_in_seconds is None or self.oldest_timestamp is None:
            return

        t = now()
        # the oldest track is still younger than the ttl
        if (t - self.ttl_in_seconds) < self.oldest_timestamp:
            return

        to_be_deleted = set()

        tracks = sorted(self._tracks.values(), key=lambda track: track.last_updated)
        for track in reversed(tracks):
            if (t - track.last_updated) < self.ttl_in_seconds:
                self.oldest_timestamp = track.last_updated
                break
            # ttl is over. delete it.
            to_be_deleted.add(track.mmsi)

        for mmsi in to_be_deleted:
            del self._tracks[mmsi]
