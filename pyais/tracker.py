"""AIS tracking functionality.
"""
import typing
import time
import dataclasses
from heapq import heapify, heappush, heappop
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
    last_updated: typing.Optional[float] = dataclasses.field(compare=False, default_factory=now)


# compute a set of all fields only once
FIELDS = dataclasses.fields(AISTrack)


def msg_to_track(msg: ANY_MESSAGE) -> AISTrack:
    """Convert a AIS message into a AISTrack.
    Only fields known to class AISTrack are considered.
    Depending on the type of the message, the implementation varies."""
    track = AISTrack(mmsi=msg.mmsi)
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
    """

    def __init__(self, ttl_in_seconds: int = 600) -> None:
        self.tracks: typing.Dict[str, AISTrack] = {}  # { mmsi: AISTrack(), ...}
        self.timestamps: typing.List[typing.Tuple[int, str]] = []  # [(ts, mmsi), ...]
        self.ttl_in_seconds: int = ttl_in_seconds  # in seconds

    def update(self, msg: AISSentence) -> None:
        decoded = msg.decode()
        mmsi = int(decoded.mmsi)
        track = msg_to_track(decoded)
        self.insert_or_update(mmsi, track)

    def insert_or_update(self, mmsi: int, track: AISTrack) -> None:
        # Does the track already exist?
        if mmsi in self.tracks:
            self.update_track(mmsi, track)
        else:
            self.insert_track(mmsi, track)

    def insert_track(self, mmsi: int, new: AISTrack) -> None:
        print(f'creating new track for {mmsi}')
        self.tracks[mmsi] = new
        heappush(self.timestamps, (new.last_updated, mmsi))  # logN
        self.cleanup()

    def update_track(self, mmsi: int, new: AISTrack) -> None:
        print(f'updating track for {mmsi}')
        old = self.tracks[mmsi]
        old = update_track(old, new)
        for i, ts in enumerate(self.timestamps):  # O(N)
            if mmsi == ts[1]:
                self.timestamps[i] = (old.last_updated, mmsi)
                heapify(self.timestamps)
        self.cleanup()

    def cleanup(self) -> None:
        t = now()
        while self.timestamps:  # N * logN
            ts, mmsi = self.timestamps[0]
            if (t - ts) < self.ttl_in_seconds:
                break
            print('ttl is over. deleting...')
            heappop(self.timestamps)
            del self.tracks[mmsi]
