"""AIS tracking functionality.The AISTracker maintains as collections
of known tracks and maintains the state of each vessel. This is
necessary because several messages can give different information
about a ship. In addition, the data changes constantly (position, speed).
Each track (or vessel) is solely identified by its MMSI.
"""
from enum import Enum
import typing
import time
import dataclasses
from pyais.messages import ANY_MESSAGE, AISSentence


def now() -> float:
    """Current time as UNIX time (milliseconds)"""
    return time.time()


class AISTrackEvent(Enum):
    CREATED = 'created'
    UPDATED = 'updated'
    DELETED = 'deleted'


class AISUpdateBroker:
    """This class propagates updates to subscribers via callbacks."""

    def __init__(self) -> None:
        self._callbacks: typing.List[typing.Tuple[AISTrackEvent, typing.Any]] = []

    def attach(self, event: AISTrackEvent, callback: typing.Any) -> None:
        """Attach a new subscriber"""
        if callback not in self._callbacks:
            self._callbacks.append((event, callback))

    def detach(self, event: AISTrackEvent, callback: typing.Any) -> None:
        """Detach a subscriber"""
        try:
            self._callbacks.remove((event, callback))
        except ValueError:
            pass

    def propagate(self, track: 'AISTrack', event: AISTrackEvent) -> None:
        """Propagate a track event"""
        for destination, callback in self._callbacks:
            if event == destination:
                callback(track)


@dataclasses.dataclass(eq=True, order=True)
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
    name: typing.Optional[str] = dataclasses.field(compare=False, default=None)
    ais_version: typing.Optional[int] = dataclasses.field(compare=False, default=None)
    ais_type: typing.Optional[str] = dataclasses.field(compare=False, default=None)
    status: typing.Optional[str] = dataclasses.field(compare=False, default=None)


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


def poplast(dictionary: typing.Dict[typing.Any, typing.Any]) -> typing.Any:
    """Get the last item of a dict non-destructively (in terms of insertion order)."""
    # On Python3.8+ reversed(dict.items()) would do the job.
    # But by doing so, support for Python3.7 would have to be dropped.
    # The fastest and most memory efficient solution for that, is this little hack.
    key, latest = dictionary.popitem()
    dictionary[key] = latest
    return latest


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

    def __init__(
        self, ttl_in_seconds: typing.Optional[int] = 600, stream_is_ordered: bool = False
    ) -> None:
        """Creates a new tracker instance.
        :param ttl_in_seconds:      the ttl in seconds before expired tracks are pruned.
        :param stream_is_ordered:   set to True if the stream of messages arrives in order.
                                    This greatly increases the efficiency of cleanup() and n_latest_tracks().
                                    By default, both methods take O(N * log(N)) time.
                                    When stream_is_ordered is True, they take O(k) with k<=N time.
                                    So if you know that your messages are ordered after their timestamps,
                                    set stream_is_ordered to True.
        """
        self._tracks: typing.Dict[int, AISTrack] = {}  # { mmsi: AISTrack(), ...}
        self.ttl_in_seconds: typing.Optional[int] = ttl_in_seconds  # in seconds or None
        self.stream_is_ordered: bool = stream_is_ordered
        self.oldest_timestamp: typing.Optional[float] = None
        self._broker = AISUpdateBroker()

    def __enter__(self) -> "AISTracker":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        return None

    def __set_oldest_timestamp(self, ts: float) -> None:
        if self.oldest_timestamp is None:
            self.oldest_timestamp = ts
        else:
            self.oldest_timestamp = min(self.oldest_timestamp, ts)

    def _tracks_ordered_after_insertion(
        self
    ) -> typing.Union[typing.List[AISTrack], typing.Iterable[AISTrack]]:
        tracks: typing.Union[typing.List[AISTrack], typing.Iterable[AISTrack]]
        if self.stream_is_ordered:
            # From Python3.7 keys are ordered after insertion in dicts.
            # No need to sort.
            tracks = self._tracks.values()
        else:
            tracks = reversed(sorted(self._tracks.values(), key=lambda track: track.last_updated))
        return tracks

    @property
    def tracks(self) -> typing.List[AISTrack]:
        """Returns a list of all known tracks."""
        return list(self._tracks.values())

    def register_callback(
        self, event: AISTrackEvent, callback: typing.Callable[[AISTrack], typing.Any]
    ) -> None:
        """Register a callback that is called every time a specific event happens.
        The callback should be function that takes an AISTrack as a single argument."""
        self._broker.attach(event, callback)

    def remove_callback(
        self, event: AISTrackEvent, callback: typing.Callable[[AISTrack], typing.Any]
    ) -> None:
        """Remove a callback. Every callback is identified by its event and callback-function."""
        self._broker.detach(event, callback)

    def update(self, msg: AISSentence, ts_epoch_ms: typing.Optional[float] = None) -> None:
        """Updates a track. If the track does not yet exist, a new track is created.
        :param msg: the message to add to the track.
        :param ts_epoch_ms: an optional timestamp to tell when the message was originally received."""
        decoded = msg.decode()
        mmsi = int(decoded.mmsi)
        track = msg_to_track(decoded, ts_epoch_ms)
        self.ensure_timestamp_constraints(track.last_updated)
        self.insert_or_update(mmsi, track)
        self.cleanup()

    def ensure_timestamp_constraints(self, ts_epoch_ms: float) -> None:
        """Ensures that tracks are ordered. Only relevant is stream_is_ordered is True."""
        if not self.stream_is_ordered or not self._tracks:
            return

        # Get the newest track
        latest = poplast(self._tracks)

        if ts_epoch_ms < latest.last_updated:
            # The new track must be inserted after the latest one.
            raise ValueError(
                'can not insert an older timestamp in a ordered stream.'
                f' {ts_epoch_ms} < {latest.last_updated}.'
                ' consider setting stream_is_ordered to False.'
            )

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
            self._broker.propagate(track, AISTrackEvent.DELETED)
            return track
        except KeyError:
            return None

    def n_latest_tracks(self, n: int) -> typing.List[AISTrack]:
        """Return the latest N tracks. These are the tracks with the youngest timestamps.
        E.g. the tracks that were updated most recently."""
        n_latest = []
        n = min(n, len(self._tracks))

        tracks = self._tracks_ordered_after_insertion()

        for i, track in enumerate(tracks):
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
        self._broker.propagate(new, AISTrackEvent.CREATED)

    def update_track(self, mmsi: int, new: AISTrack) -> None:
        """Updates an existing track in memory"""
        old = self._tracks[mmsi]
        if new.last_updated < old.last_updated:
            raise ValueError('cannot update track with older message')

        updated = update_track(old, new)
        # Neat little trick to keep tracks ordered after timestamp
        del self._tracks[mmsi]
        self._tracks[mmsi] = updated
        self._broker.propagate(updated, AISTrackEvent.UPDATED)

    def cleanup(self) -> None:
        """Delete all records whose last update is older than ttl."""
        if self.ttl_in_seconds is None or self.oldest_timestamp is None:
            return

        t = now()
        # the oldest track is still younger than the ttl
        if (t - self.ttl_in_seconds) < self.oldest_timestamp:
            return

        to_be_deleted = set()
        tracks = self._tracks_ordered_after_insertion()

        for track in tracks:
            if (t - track.last_updated) < self.ttl_in_seconds:
                self.oldest_timestamp = track.last_updated
                break
            # ttl is over. delete it.
            to_be_deleted.add(track.mmsi)

        for mmsi in to_be_deleted:
            self.pop_track(mmsi)
