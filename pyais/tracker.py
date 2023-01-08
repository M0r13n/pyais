"""AIS tracking functionality.
"""
import typing
import time
import dataclasses
from heapq import heapify, heappush, heappop, nlargest
from pyais.messages import ANY_MESSAGE, AISSentence


def now() -> float:
    """Current time as UNIX time (milliseconds)"""
    return time.time()


@dataclasses.dataclass(eq=True, order=True, slots=True)
class AISTrack:
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
    ts_epoch_ms can be used as a timestamp for when the message was initially received."""
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
    """Updates all fields of old with the values of new."""
    for field in FIELDS:
        new_val = getattr(new, field.name)
        if new_val is not None:
            setattr(old, field.name, new_val)
    return old


class AISTracker:
    """
    An AIS tracker receives AIS messages and maintains a collection of known tracks.
    Set the ttl to None to never clean up.
    """

    def __init__(self, ttl_in_seconds: typing.Optional[int] = 600) -> None:
        self.tracks: typing.Dict[int, AISTrack] = {}  # { mmsi: AISTrack(), ...}
        self.timestamps: typing.List[typing.Tuple[float, int]] = []  # [(ts, mmsi), ...]
        self.ttl_in_seconds: typing.Optional[int] = ttl_in_seconds  # in seconds or None

    def __enter__(self) -> "AISTracker":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        del self.tracks
        del self.timestamps
        return None

    def update(self, msg: AISSentence, ts_epoch_ms: typing.Optional[float] = None) -> None:
        decoded = msg.decode()
        mmsi = int(decoded.mmsi)
        track = msg_to_track(decoded, ts_epoch_ms)
        self.insert_or_update(mmsi, track)

    def get_track(self, mmsi: typing.Union[str, int]) -> typing.Optional[AISTrack]:
        try:
            return self.tracks[int(mmsi)]
        except KeyError:
            return None

    def n_latest_tracks(self, n: int) -> typing.List[AISTrack]:
        n_latest = nlargest(n, self.timestamps)
        result = [self.tracks[x[1]] for x in n_latest]
        return result

    def insert_or_update(self, mmsi: int, track: AISTrack) -> None:
        # Does the track already exist?
        if mmsi in self.tracks:
            self.update_track(mmsi, track)
        else:
            self.insert_track(mmsi, track)

    def insert_track(self, mmsi: int, new: AISTrack) -> None:
        self.tracks[mmsi] = new
        heappush(self.timestamps, (new.last_updated, mmsi))
        self.cleanup()

    def update_track(self, mmsi: int, new: AISTrack) -> None:
        old = self.tracks[mmsi]
        old = update_track(old, new)
        for i, ts in enumerate(self.timestamps):  # O(N)
            if mmsi == ts[1]:
                self.timestamps[i] = (old.last_updated, mmsi)
                heapify(self.timestamps)
        self.cleanup()

    def cleanup(self) -> None:
        """Delete all records whose last update is older than ttl."""
        if self.ttl_in_seconds is None:
            return

        t = now()
        while self.timestamps:
            ts, mmsi = self.timestamps[0]
            if (t - ts) < self.ttl_in_seconds:
                break
            # ttl is over. delete it.
            heappop(self.timestamps)
            del self.tracks[mmsi]
