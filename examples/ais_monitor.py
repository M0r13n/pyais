#!/usr/bin/env python3
"""
ais_monitor.py — A btop-like TUI for real-time AIS ship traffic monitoring.

Requirements:
    pip install pyais

Usage:
    python ais_monitor.py [--host HOST] [--port PORT]

Default: Norwegian Coastal Administration AIS feed (153.44.253.27:5631)

Controls:
    q           Quit
    Space       Pause / Resume (data keeps arriving in background)
    Tab         Switch panel focus (Ships ↔ Messages)
    ↑ / ↓       Navigate / scroll
    PgUp / PgDn Page scroll
    Home / End  Jump to top / bottom
    Enter / d   Open ship detail view
    f           Enter filter mode
    t           Toggle tracking for selected ship
    s           Cycle sort column
    r           Reverse sort order
    h           Toggle highlight for tracked ships
    n           Toggle show only named ships
    p           Toggle show only ships with position
    c           Clear all filters

Filter syntax (press f):
    mmsi:257*           MMSI glob pattern
    name:*VIKING*       Ship name glob
    type:1,2,3          AIS message types
    callsign:LA*        Callsign glob
    dest:*BERGEN*       Destination glob

    shiptype:cargo      Ship-type group name
    shiptype:military   Ship-type group name
    shiptype:cargo,tanker,military   Multiple groups (OR)
    shiptype:*pass*     Glob on displayed type label
    shiptype:35         Numeric AIS ship-type code
    shiptype:70-79      Numeric code range

    Groups: wig fishing towing dredging diving military sailing
            pleasure hsc pilot sar tug tender passenger cargo
            tanker other

    speed>10            Speed over 10 kn
    speed<5             Speed under 5 kn
    lat>60              Latitude north of 60°
    lon<10              Longitude west of 10°
    tracked             Only tracked ships

    Multiple tokens are combined with AND logic.
"""

from datetime import datetime, timezone
from collections import deque, OrderedDict
import time
import threading
import fnmatch
import argparse
import sys
import locale

locale.setlocale(locale.LC_ALL, "")

try:
    import curses
except ImportError:
    print("Error: curses module not available.")
    if sys.platform == "win32":
        print("On Windows install:  pip install windows-curses")
    sys.exit(1)

try:
    from pyais.stream import TCPConnection
except ImportError:
    print("Error: pyais is required.  pip install pyais")
    sys.exit(1)


DEFAULT_HOST = "153.44.253.27"
DEFAULT_PORT = 5631
MAX_MESSAGES = 5000
MAX_SHIPS = 10000
RATE_WINDOW = 10
REFRESH_MS = 200

NAV_STATUS = {
    0: "Underway/Engine",
    1: "At Anchor",
    2: "Not Commanding",
    3: "Restricted Mnvr",
    4: "Draught Constr.",
    5: "Moored",
    6: "Aground",
    7: "Fishing",
    8: "Underway/Sail",
    9: "HSC",
    10: "WIG",
    11: "Towing Astern",
    12: "Towing Ahead",
    14: "SART/MOB/EPIRB",
    15: "Undefined",
}

_SHIP_TYPE_RANGES = {
    (20, 29): "WIG",
    (30, 30): "Fishing",
    (31, 32): "Towing",
    (33, 33): "Dredging",
    (34, 34): "Diving",
    (35, 35): "Military",
    (36, 36): "Sailing",
    (37, 37): "Pleasure",
    (40, 49): "HSC",
    (50, 50): "Pilot",
    (51, 51): "SAR",
    (52, 52): "Tug",
    (53, 53): "Port Tender",
    (54, 54): "Anti-Pollut.",
    (55, 55): "Law Enforc.",
    (58, 58): "Medical",
    (59, 59): "Noncombatant",
    (60, 69): "Passenger",
    (70, 79): "Cargo",
    (80, 89): "Tanker",
    (90, 99): "Other",
}


def ship_type_str(code: int | None) -> str:
    if code is None or code == 0:
        return ""
    for (lo, hi), label in _SHIP_TYPE_RANGES.items():
        if lo <= code <= hi:
            return label
    return str(code)


SHIP_TYPE_GROUPS: dict[str, set[int]] = {
    "wig": set(range(20, 30)),
    "fishing": {30},
    "towing": {31, 32},
    "dredging": {33},
    "diving": {34},
    "military": {35},
    "sailing": {36},
    "pleasure": {37},
    "hsc": set(range(40, 50)),
    "pilot": {50},
    "sar": {51},
    "tug": {52},
    "tender": {53},
    "antipollution": {54},
    "lawenforcement": {55},
    "law": {55},
    "medical": {58},
    "noncombatant": {59},
    "passenger": set(range(60, 70)),
    "cargo": set(range(70, 80)),
    "tanker": set(range(80, 90)),
    "other": set(range(90, 100)),
}


class ShipRecord:
    __slots__ = (
        "mmsi", "name", "ship_type", "msg_type",
        "lat", "lon", "speed", "course", "heading",
        "status", "turn", "destination", "callsign",
        "imo", "draught", "last_seen", "msg_count", "tracked",
    )

    def __init__(self, mmsi: int) -> None:
        self.mmsi: int = mmsi
        self.name: str = ""
        self.ship_type: str | None = None
        self.msg_type: int = 0
        self.lat: float | None = None
        self.lon: float | None = None
        self.speed: float | None = None
        self.course: float | None = None
        self.heading: float | None = None
        self.status: int | None = None
        self.turn: float | None = None
        self.destination: str = ""
        self.callsign: str = ""
        self.imo: str | None = None
        self.draught: float | None = None
        self.last_seen: datetime | None = None
        self.msg_count: int = 0
        self.tracked: bool = False

    def copy(self) -> 'ShipRecord':
        clone = ShipRecord.__new__(ShipRecord)
        for attr in ShipRecord.__slots__:
            setattr(clone, attr, getattr(self, attr))
        return clone

    def update(self, d: dict[str, object]) -> None:
        self.msg_count += 1
        self.last_seen = datetime.now(timezone.utc)
        self.msg_type = int(d.get("msg_type", self.msg_type))  # type: ignore

        lat: float | None = d.get("lat")  # type: ignore
        if lat is not None and -90 <= lat <= 90 and abs(lat - 91.0) > 0.1:
            self.lat = lat
        lon: float | None = d.get("lon")  # type: ignore
        if lon is not None and -180 <= lon <= 180 and abs(lon - 181.0) > 0.1:
            self.lon = lon
        spd: float | None = d.get("speed")  # type: ignore
        if spd is not None and 0 <= spd <= 102.2:
            self.speed = spd
        cog: float | None = d.get("course")  # type: ignore
        if cog is not None and 0 <= cog <= 360:
            self.course = cog
        hdg: float | None = d.get("heading")  # type: ignore
        if hdg is not None and hdg != 511:
            self.heading = hdg
        st = d.get("status")
        if st is not None:
            self.status = st  # type: ignore
        trn = d.get("turn")
        if trn is not None:
            self.turn = trn   # type: ignore

        for attr in ("ship_type", "imo", "draught"):
            v = d.get(attr)
            if v is not None and v != 0:
                setattr(self, attr, v)

        for attr, key in (
            ("name", "shipname"),
            ("callsign", "callsign"),
            ("destination", "destination"),
        ):
            v = d.get(key)
            if v and isinstance(v, str) and v.strip():
                setattr(self, attr, v.strip())


class MessageRecord:
    __slots__ = ("timestamp", "data", "mmsi", "msg_type")

    def __init__(self, data: dict[str, object]):
        self.timestamp = datetime.now(timezone.utc)
        self.data = data
        self.mmsi = data.get("mmsi", 0)
        self.msg_type = data.get("msg_type", 0)

    def copy(self) -> 'MessageRecord':
        clone = MessageRecord.__new__(MessageRecord)
        clone.timestamp = self.timestamp
        clone.data = self.data
        clone.mmsi = self.mmsi
        clone.msg_type = self.msg_type
        return clone

    def format(self, width: int = 120) -> str:
        ts = self.timestamp.strftime("%H:%M:%S")
        parts = [ts, f"[{self.msg_type:>2}]", f"MMSI:{self.mmsi}"]
        d = self.data
        nm: str | None = d.get("shipname")  # type: ignore
        if nm and nm.strip():
            parts.append(f"Name:{nm.strip()}")
        lat: float | None = d.get("lat")   # type: ignore
        lon: float | None = d.get("lon")   # type: ignore
        if lat is not None and lon is not None and abs(lat) <= 90 and abs(lon) <= 180:
            parts.append(f"Pos:{lat:.4f},{lon:.4f}")
        spd: float | None = d.get("speed")  # type: ignore
        if spd is not None and spd <= 102.2:
            parts.append(f"SOG:{spd:.1f}")
        cog: float | None = d.get("course")  # type: ignore
        if cog is not None and cog <= 360:
            parts.append(f"COG:{cog:.1f}")
        dest: str | None = d.get("destination")  # type: ignore
        if dest and dest.strip():
            parts.append(f"Dest:{dest.strip()}")
        return " ".join(parts)[:width]


class DataStore:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.ships: OrderedDict[int, ShipRecord] = OrderedDict()
        self.messages: deque[MessageRecord] = deque(maxlen=MAX_MESSAGES)
        self.total_msgs = 0
        self.errors = 0
        self.connected = False
        self.conn_error = ""
        self._rate_ts: deque[float] = deque(maxlen=2000)
        self.tracked_mmsis: set[int] = set()

    def add_message(self, data: dict):
        mmsi = data.get("mmsi")
        if mmsi is None:
            return
        with self.lock:
            self.total_msgs += 1
            self._rate_ts.append(time.monotonic())
            if mmsi not in self.ships:
                if len(self.ships) >= MAX_SHIPS:
                    self.ships.popitem(last=False)
                self.ships[mmsi] = ShipRecord(mmsi)
            ship = self.ships[mmsi]
            ship.tracked = mmsi in self.tracked_mmsis
            ship.update(data)
            self.messages.append(MessageRecord(data))

    def get_rate(self) -> float:
        now = time.monotonic()
        with self.lock:
            cnt = sum(1 for t in self._rate_ts if t >= now - RATE_WINDOW)
        return cnt / RATE_WINDOW

    def snapshot_ships_copy(self) -> list[ShipRecord]:
        with self.lock:
            return [s.copy() for s in self.ships.values()]

    def snapshot_ships(self) -> list[ShipRecord]:
        with self.lock:
            return list(self.ships.values())

    def snapshot_messages_copy(self, n: int = 500) -> list[MessageRecord]:
        with self.lock:
            return [m.copy() for m in list(self.messages)[-n:]]

    def snapshot_messages(self, n: int = 500) -> list[MessageRecord]:
        with self.lock:
            return list(self.messages)[-n:]

    def toggle_track(self, mmsi: int) -> bool:
        with self.lock:
            if mmsi in self.tracked_mmsis:
                self.tracked_mmsis.discard(mmsi)
                if mmsi in self.ships:
                    self.ships[mmsi].tracked = False
                return False
            self.tracked_mmsis.add(mmsi)
            if mmsi in self.ships:
                self.ships[mmsi].tracked = True
            return True

    def stats(self) -> dict:
        with self.lock:
            return dict(
                total=self.total_msgs,
                ships=len(self.ships),
                tracked=len(self.tracked_mmsis),
                errors=self.errors,
                connected=self.connected,
                conn_error=self.conn_error,
            )


class FilterEngine:
    def __init__(self):
        self.rules: list[tuple[str, str, str]] = []
        self.text = ""

    def parse(self, text: str):
        self.text = text.strip()
        self.rules = []
        if not self.text:
            return
        for tok in self.text.split():
            if tok.lower() == "tracked":
                self.rules.append(("tracked", ":", ""))
                continue
            for op in (">=", "<=", ">", "<", ":", "="):
                if op in tok:
                    field, _, val = tok.partition(op)
                    if field and val:
                        self.rules.append((field.lower(), op, val))
                    break

    def matches(self, ship: ShipRecord) -> bool:
        return all(self._check(ship, f, o, v) for f, o, v in self.rules)

    @staticmethod
    def _match_shiptype(ship_type_code, val: str) -> bool:
        if ship_type_code is None or ship_type_code == 0:
            return False
        label = ship_type_str(ship_type_code).upper()
        for tok in val.split(","):
            tok = tok.strip()
            if not tok:
                continue
            tok_lower = tok.lower()
            if tok_lower in SHIP_TYPE_GROUPS:
                if ship_type_code in SHIP_TYPE_GROUPS[tok_lower]:
                    return True
                continue
            if "-" in tok:
                parts = tok.split("-", 1)
                if parts[0].isdigit() and parts[1].isdigit():
                    lo, hi = int(parts[0]), int(parts[1])
                    if lo <= ship_type_code <= hi:
                        return True
                    continue
            if tok.isdigit():
                if ship_type_code == int(tok):
                    return True
                continue
            if fnmatch.fnmatch(label, tok.upper()):
                return True
        return False

    def _check(self, s: ShipRecord, field: str, op: str, val: str) -> bool:
        if field == "tracked":
            return s.tracked
        if field == "mmsi":
            return fnmatch.fnmatch(str(s.mmsi), val)
        if field == "name":
            return fnmatch.fnmatch(s.name.upper(), val.upper())
        if field == "callsign":
            return fnmatch.fnmatch(s.callsign.upper(), val.upper())
        if field == "dest":
            return fnmatch.fnmatch(s.destination.upper(), val.upper())
        if field == "type":
            types = {int(t) for t in val.split(",") if t.strip().isdigit()}
            return s.msg_type in types
        if field == "shiptype":
            return self._match_shiptype(s.ship_type, val)

        actual = None
        if field == "speed":
            actual = s.speed
        elif field == "lat":
            actual = s.lat
        elif field == "lon":
            actual = s.lon
        elif field == "course":
            actual = s.course
        elif field == "heading":
            actual = s.heading
        elif field == "msgs":
            actual = s.msg_count
        else:
            return True

        if actual is None:
            return False
        try:
            ev = float(val)
        except ValueError:
            return True
        if op == ">":
            return actual > ev
        if op == "<":
            return actual < ev
        if op == ">=":
            return actual >= ev
        if op == "<=":
            return actual <= ev
        return abs(actual - ev) < 0.01

    def apply(self, ships: list[ShipRecord]) -> list[ShipRecord]:
        if not self.rules:
            return ships
        return [s for s in ships if self.matches(s)]

    @property
    def active(self) -> bool:
        return bool(self.rules)


class Receiver(threading.Thread):
    def __init__(self, store: DataStore, host: str, port: int):
        super().__init__(daemon=True)
        self.store = store
        self.host = host
        self.port = port
        self.running = True

    def run(self):
        while self.running:
            try:
                self.store.conn_error = f"Connecting to {self.host}:{self.port}\u2026"
                self.store.connected = False
                for msg in TCPConnection(self.host, port=self.port):
                    if not self.running:
                        return
                    self.store.connected = True
                    self.store.conn_error = ""
                    try:
                        decoded = msg.decode()
                        if decoded is not None:
                            data = decoded.asdict()
                            if isinstance(data, dict):
                                self.store.add_message(data)
                            elif isinstance(data, (list, tuple)):
                                for d in data:
                                    if isinstance(d, dict):
                                        self.store.add_message(d)
                    except Exception:
                        with self.store.lock:
                            self.store.errors += 1
            except Exception as exc:
                self.store.connected = False
                self.store.conn_error = str(exc)[:60]
                if self.running:
                    time.sleep(5)


SORT_KEYS = [
    "mmsi", "name", "type", "lat", "lon",
    "speed", "course", "msgs", "last_seen",
]

ALL_COLUMNS = [
    ("T", 1), ("MMSI", 10), ("Name", 18), ("Type", 10),
    ("Lat", 9), ("Lon", 10), ("SOG", 5), ("COG", 5),
    ("HDG", 4), ("Status", 15), ("Dest", 14), ("#Msg", 5), ("Seen", 8),
]

_COL_SORT = {
    "T": "", "MMSI": "mmsi", "Name": "name", "Type": "type",
    "Lat": "lat", "Lon": "lon", "SOG": "speed", "COG": "course",
    "HDG": "", "Status": "", "Dest": "", "#Msg": "msgs", "Seen": "last_seen",
}


class App:
    def __init__(self, scr, store: DataStore, host: str, port: int):
        self.scr = scr
        self.store = store
        self.host = host
        self.port = port
        self.alive = True

        self.panel = 0
        self.sel = 0
        self.ship_off = 0
        self.msg_off = 0
        self.sort_idx = 0
        self.sort_rev = False

        self.hl_tracked = True
        self.only_named = False
        self.only_pos = False

        self.paused = False
        self._frozen_ships: list[ShipRecord] | None = None
        self._frozen_msgs: list[MessageRecord] | None = None
        self._frozen_stats: dict | None = None
        self._frozen_rate: float = 0.0
        self._pause_time: datetime | None = None

        self.filt = FilterEngine()
        self.filt_mode = False
        self.filt_buf = ""

        self.detail = False
        self.detail_mmsi: int | None = None

        self._ships: list[ShipRecord] = []
        self._msgs: list[MessageRecord] = []

        self._init_curses()

    def _init_curses(self):
        curses.curs_set(0)
        self.scr.nodelay(True)
        self.scr.timeout(REFRESH_MS)
        curses.noecho()
        curses.cbreak()
        self.scr.keypad(True)
        try:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
            curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_GREEN)
            curses.init_pair(5, curses.COLOR_RED, -1)
            curses.init_pair(6, curses.COLOR_WHITE, -1)
            curses.init_pair(7, curses.COLOR_CYAN, -1)
            curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_BLUE)
            curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_YELLOW)
            curses.init_pair(10, curses.COLOR_WHITE, curses.COLOR_RED)
        except curses.error:
            pass

    def _toggle_pause(self):
        if self.paused:
            self.paused = False
            self._frozen_ships = None
            self._frozen_msgs = None
            self._frozen_stats = None
            self._frozen_rate = 0.0
            self._pause_time = None
        else:
            self.paused = True
            self._pause_time = datetime.now(timezone.utc)
            self._frozen_ships = self.store.snapshot_ships_copy()
            self._frozen_msgs = self.store.snapshot_messages_copy(500)
            self._frozen_stats = self.store.stats()
            self._frozen_rate = self.store.get_rate()

    def _get_ships(self) -> list[ShipRecord]:
        if self.paused and self._frozen_ships is not None:
            return list(self._frozen_ships)
        return self.store.snapshot_ships()

    def _get_msgs(self) -> list[MessageRecord]:
        if self.paused and self._frozen_msgs is not None:
            return list(self._frozen_msgs)
        return self.store.snapshot_messages(500)

    def _get_stats(self) -> dict:
        if self.paused and self._frozen_stats is not None:
            return dict(self._frozen_stats)
        return self.store.stats()

    def _get_rate(self) -> float:
        if self.paused:
            return self._frozen_rate
        return self.store.get_rate()

    def run(self):
        while self.alive:
            try:
                self._input()
                self._draw()
            except KeyboardInterrupt:
                self.alive = False
            except curses.error:
                pass

    def _input(self):
        try:
            k = self.scr.getch()
        except curses.error:
            return
        if k == -1:
            return
        if self.filt_mode:
            return self._input_filter(k)
        if self.detail:
            return self._input_detail(k)
        self._input_main(k)

    def _input_main(self, k):
        if k in (ord("q"), ord("Q")):
            self.alive = False
        elif k == ord(" "):
            self._toggle_pause()
        elif k == 9:
            self.panel = 1 - self.panel
        elif k in (ord("f"), ord("F")):
            self.filt_mode = True
            self.filt_buf = self.filt.text
        elif k in (ord("t"), ord("T")):
            self._track_sel()
        elif k in (ord("s"), ord("S")):
            self.sort_idx = (self.sort_idx + 1) % len(SORT_KEYS)
        elif k in (ord("r"), ord("R")):
            self.sort_rev = not self.sort_rev
        elif k in (ord("h"), ord("H")):
            self.hl_tracked = not self.hl_tracked
        elif k in (ord("n"), ord("N")):
            self.only_named = not self.only_named
            self.sel = 0
        elif k in (ord("p"), ord("P")):
            self.only_pos = not self.only_pos
            self.sel = 0
        elif k in (ord("c"), ord("C")):
            self.filt.parse("")
            self.sel = 0
        elif k in (ord("d"), ord("D"), 10, curses.KEY_ENTER):
            self._open_detail()
        elif k == curses.KEY_UP:
            if self.panel == 0:
                self.sel = max(0, self.sel - 1)
            else:
                self.msg_off = max(0, self.msg_off - 1)
        elif k == curses.KEY_DOWN:
            if self.panel == 0:
                self.sel += 1
            else:
                self.msg_off += 1
        elif k == curses.KEY_PPAGE:
            if self.panel == 0:
                self.sel = max(0, self.sel - 20)
            else:
                self.msg_off = max(0, self.msg_off - 20)
        elif k == curses.KEY_NPAGE:
            if self.panel == 0:
                self.sel += 20
            else:
                self.msg_off += 20
        elif k == curses.KEY_HOME:
            self.sel = 0
            self.msg_off = 0
        elif k == curses.KEY_END:
            if self.panel == 0:
                self.sel = max(0, len(self._ships) - 1)
            else:
                self.msg_off = max(0, len(self._msgs) - 1)
        elif k == curses.KEY_RESIZE:
            self.scr.clear()

    def _input_filter(self, k):
        if k == 27:
            self.filt_mode = False
        elif k in (10, curses.KEY_ENTER):
            self.filt_mode = False
            self.filt.parse(self.filt_buf)
            self.sel = 0
        elif k in (curses.KEY_BACKSPACE, 127, 8):
            self.filt_buf = self.filt_buf[:-1]
        elif 32 <= k <= 126:
            self.filt_buf += chr(k)

    def _input_detail(self, k):
        if k == ord(" "):
            self._toggle_pause()
        elif k in (27, ord("d"), ord("D"), ord("q"), ord("Q")):
            self.detail = False
        elif k in (ord("t"), ord("T")) and self.detail_mmsi is not None:
            self.store.toggle_track(self.detail_mmsi)

    def _track_sel(self):
        if self._ships and 0 <= self.sel < len(self._ships):
            self.store.toggle_track(self._ships[self.sel].mmsi)

    def _open_detail(self):
        if self._ships and 0 <= self.sel < len(self._ships):
            self.detail_mmsi = self._ships[self.sel].mmsi
            self.detail = True

    def _sorted(self, ships: list[ShipRecord]) -> list[ShipRecord]:
        key = SORT_KEYS[self.sort_idx]
        attr_map = dict(
            mmsi="mmsi", name="name", type="ship_type",
            lat="lat", lon="lon", speed="speed",
            course="course", msgs="msg_count", last_seen="last_seen",
        )
        none_map = dict(
            mmsi=0, name="zzz", type=9999,
            lat=999.0, lon=999.0, speed=-1.0,
            course=999.0, msgs=0,
            last_seen=datetime.min.replace(tzinfo=timezone.utc),
        )
        attr = attr_map.get(key, "mmsi")
        nv = none_map.get(key, 0)

        def sk(s):
            v = getattr(s, attr)
            if v is None:
                return nv
            return v.lower() if isinstance(v, str) else v

        return sorted(ships, key=sk, reverse=self.sort_rev)

    @staticmethod
    def _fit_cols(w: int):
        result = []
        used = 0
        for name, cw in ALL_COLUMNS:
            need = cw + (1 if result else 0)
            if used + need <= w:
                result.append((name, cw))
                used += need
        return result or [("MMSI", 10)]

    def _put(self, y, x, s, attr=curses.A_NORMAL):
        h, w = self.scr.getmaxyx()
        if 0 <= y < h and 0 <= x < w:
            try:
                self.scr.addnstr(y, x, s, w - x, attr)
            except curses.error:
                pass

    def _draw(self):
        self.scr.erase()
        h, w = self.scr.getmaxyx()
        if h < 8 or w < 30:
            self._put(0, 0, "Terminal too small!", curses.A_BOLD)
            self.scr.refresh()
            return
        if self.detail:
            self._draw_detail(h, w)
        else:
            self._draw_main(h, w)
        self.scr.refresh()

    def _draw_main(self, h, w):
        ships = self._get_ships()
        if self.only_named:
            ships = [s for s in ships if s.name]
        if self.only_pos:
            ships = [s for s in ships if s.lat is not None and s.lon is not None]
        ships = self.filt.apply(ships)
        ships = self._sorted(ships)
        self._ships = ships
        self._msgs = self._get_msgs()

        if self._ships:
            self.sel = max(0, min(self.sel, len(self._ships) - 1))
        else:
            self.sel = 0

        body = h - 4
        ships_h = max(4, int(body * 0.65))
        msgs_h = body - ships_h

        y = self._draw_header(0, w)
        y = self._draw_ships(y, w, ships_h)
        y = self._draw_msgs(y, w, msgs_h)
        self._draw_footer(h - 2, w)

    def _draw_header(self, y, w):
        st = self._get_stats()
        rate = self._get_rate()

        conn = (
            "\u25cf Connected"
            if st["connected"]
            else "\u25cb " + (st["conn_error"] or "Disconnected")
        )
        title = f" AIS Monitor \u2502 {self.host}:{self.port} \u2502 {conn}"

        if self.paused and self._pause_time:
            since = self._pause_time.strftime("%H:%M:%S")
            title += f" \u2502 \u23f8  PAUSED since {since}"

        title_attr = (
            curses.color_pair(10) | curses.A_BOLD
            if self.paused
            else curses.color_pair(1) | curses.A_BOLD
        )
        self._put(y, 0, title.ljust(w)[:w], title_attr)

        sname = SORT_KEYS[self.sort_idx]
        arrow = "\u25bc" if self.sort_rev else "\u25b2"
        flags = []
        if self.paused:
            flags.append("PAUSED")
        if self.only_named:
            flags.append("Named")
        if self.only_pos:
            flags.append("Pos")
        if self.hl_tracked:
            flags.append("HL")
        ftag = " [" + ",".join(flags) + "]" if flags else ""
        line = (
            f" Ships:{st['ships']:,}"
            f" Shown:{len(self._ships):,}"
            f" Msgs:{st['total']:,}"
            f" {rate:.1f}/s"
            f" Tracked:{st['tracked']}"
            f" Err:{st['errors']}"
            f" Sort:{sname}{arrow}{ftag}"
        )
        stat_attr = (
            curses.color_pair(9) | curses.A_BOLD
            if self.paused
            else curses.color_pair(4)
        )
        self._put(y + 1, 0, line.ljust(w)[:w], stat_attr)
        return y + 2

    def _draw_ships(self, y, w, max_h):
        active = self.panel == 0
        bc = curses.color_pair(7) if active else curses.color_pair(6)

        label = "\u2500 Ships "
        if self.filt.active:
            label += f"[{self.filt.text}] "
        if self.paused:
            label += "\u23f8 "
        label += "\u2500" * max(0, w - len(label))
        self._put(y, 0, label[:w], bc | curses.A_BOLD)
        y += 1

        cols = self._fit_cols(w)
        hdr_parts = []
        cur_sort = SORT_KEYS[self.sort_idx]
        for name, cw in cols:
            s = name
            if _COL_SORT.get(name) == cur_sort and cur_sort:
                s += "\u25bc" if self.sort_rev else "\u25b2"
            hdr_parts.append(s.ljust(cw)[:cw])
        self._put(
            y, 0, " ".join(hdr_parts).ljust(w)[:w],
            curses.color_pair(8) | curses.A_BOLD,
        )
        y += 1

        rows = max_h - 2
        if self.sel >= self.ship_off + rows:
            self.ship_off = self.sel - rows + 1
        if self.sel < self.ship_off:
            self.ship_off = self.sel

        for i in range(rows):
            idx = self.ship_off + i
            if idx >= len(self._ships):
                self._put(y + i, 0, " " * w)
                continue
            ship = self._ships[idx]
            line = self._fmt_ship(ship, cols)
            attr = curses.A_NORMAL
            if idx == self.sel and active:
                attr = curses.color_pair(2) | curses.A_BOLD
            elif ship.tracked and self.hl_tracked:
                attr = curses.color_pair(3) | curses.A_BOLD
            self._put(y + i, 0, line.ljust(w)[:w], attr)
        return y + rows

    def _fmt_ship(self, s: ShipRecord, cols) -> str:
        def cell(name):
            if name == "T":
                return "\u2605" if s.tracked else " "
            if name == "MMSI":
                return str(s.mmsi)
            if name == "Name":
                return s.name or ""
            if name == "Type":
                return ship_type_str(s.ship_type)
            if name == "Lat":
                return f"{s.lat:.4f}" if s.lat is not None else ""
            if name == "Lon":
                return f"{s.lon:.4f}" if s.lon is not None else ""
            if name == "SOG":
                return f"{s.speed:.1f}" if s.speed is not None else ""
            if name == "COG":
                return f"{s.course:.1f}" if s.course is not None else ""
            if name == "HDG":
                return str(s.heading) if s.heading is not None else ""
            if name == "Status":
                return NAV_STATUS.get(s.status, "") if s.status is not None else ""
            if name == "Dest":
                return s.destination or ""
            if name == "#Msg":
                return str(s.msg_count)
            if name == "Seen":
                return s.last_seen.strftime("%H:%M:%S") if s.last_seen else ""
            return ""
        return " ".join(cell(n).ljust(cw)[:cw] for n, cw in cols)

    def _draw_msgs(self, y, w, max_h):
        active = self.panel == 1
        bc = curses.color_pair(7) if active else curses.color_pair(6)

        label = f"\u2500 Messages ({len(self._msgs):,}) "
        if self.paused:
            label += "\u23f8 "
        label += "\u2500" * max(0, w - len(label))
        self._put(y, 0, label[:w], bc | curses.A_BOLD)
        y += 1

        rows = max_h - 1
        total = len(self._msgs)
        max_off = max(0, total - rows)

        if not active:
            self.msg_off = max_off
        else:
            self.msg_off = max(0, min(self.msg_off, max_off))

        tracked = self.store.tracked_mmsis
        for i in range(rows):
            idx = self.msg_off + i
            if idx >= total:
                break
            msg = self._msgs[idx]
            attr = curses.A_NORMAL
            if self.hl_tracked and msg.mmsi in tracked:
                attr = curses.color_pair(3)
            self._put(y + i, 0, msg.format(w)[:w], attr)
        return y + rows

    def _draw_footer(self, y, w):
        if self.filt_mode:
            prompt = f" Filter: {self.filt_buf}\u2588"
            self._put(y, 0, prompt.ljust(w)[:w], curses.color_pair(9) | curses.A_BOLD)
            hint = (
                " Enter:Apply  Esc:Cancel \u2502"
                " mmsi:257* name:*SHIP* shiptype:military,cargo speed>10 tracked"
            )
            self._put(y + 1, 0, hint.ljust(w)[:w], curses.color_pair(1))
        else:
            pause_label = "\u25b6Resume" if self.paused else "\u23f8Pause"
            keys = (
                f" Q:Quit Space:{pause_label} Tab:Panel F:Filter T:Track S:Sort"
                " R:Rev H:HL N:Named P:Pos C:Clear D:Detail"
            )
            self._put(y, 0, keys.ljust(w)[:w], curses.color_pair(1))

            if self.filt.active:
                fl = f" Filter: {self.filt.text}"
                self._put(y + 1, 0, fl.ljust(w)[:w], curses.color_pair(9))
            elif self.paused:
                since = self._pause_time.strftime("%H:%M:%S") if self._pause_time else ""
                live_total = self.store.stats()["total"]
                frozen_total = self._frozen_stats.get("total", 0) if self._frozen_stats else 0
                buffered = live_total - frozen_total
                pl = (
                    f" \u23f8 PAUSED since {since}"
                    f" \u2502 {buffered:,} new messages buffered"
                    f" \u2502 Press Space to resume"
                )
                self._put(
                    y + 1, 0,
                    pl.ljust(w)[:w],
                    curses.color_pair(10) | curses.A_BOLD,
                )
            else:
                self._put(
                    y + 1, 0,
                    " No active filter".ljust(w)[:w],
                    curses.color_pair(4),
                )

    def _draw_detail(self, h, w):
        ship = None
        for s in self._get_ships():
            if s.mmsi == self.detail_mmsi:
                ship = s
                break
        if not ship:
            self.detail = False
            return

        title = f" Ship Detail: {ship.mmsi}"
        if ship.tracked:
            title += " \u2605 TRACKED"
        if self.paused:
            title += " \u2502 \u23f8 PAUSED"
        title_attr = (
            curses.color_pair(10) | curses.A_BOLD
            if self.paused
            else curses.color_pair(1) | curses.A_BOLD
        )
        self._put(0, 0, title.ljust(w)[:w], title_attr)

        fields = [
            ("MMSI", str(ship.mmsi)),
            ("Name", ship.name or "N/A"),
            ("Callsign", ship.callsign or "N/A"),
            ("IMO", str(ship.imo) if ship.imo else "N/A"),
            (
                "Ship Type",
                f"{ship_type_str(ship.ship_type)} ({ship.ship_type})"
                if ship.ship_type else "N/A",
            ),
            ("", ""),
            ("Latitude", f"{ship.lat:.6f}" if ship.lat is not None else "N/A"),
            ("Longitude", f"{ship.lon:.6f}" if ship.lon is not None else "N/A"),
            ("Speed (SOG)", f"{ship.speed:.1f} kn" if ship.speed is not None else "N/A"),
            ("Course (COG)", f"{ship.course:.1f}\u00b0" if ship.course is not None else "N/A"),
            ("Heading", f"{ship.heading}\u00b0" if ship.heading is not None else "N/A"),
            ("Turn Rate", str(ship.turn) if ship.turn is not None else "N/A"),
            ("", ""),
            ("Nav Status", NAV_STATUS.get(ship.status, "N/A") if ship.status is not None else "N/A"),
            ("Destination", ship.destination or "N/A"),
            ("Draught", f"{ship.draught} m" if ship.draught else "N/A"),
            ("", ""),
            ("Messages Rx", str(ship.msg_count)),
            ("Last Msg Type", str(ship.msg_type)),
            ("Last Seen", ship.last_seen.strftime("%Y-%m-%d %H:%M:%S UTC") if ship.last_seen else "N/A"),
            ("Tracked", "Yes \u2605" if ship.tracked else "No"),
            ("VesselFinder", f"https://www.vesselfinder.com/vessels/details/{ship.mmsi}"),
        ]

        y = 2
        for label, value in fields:
            if y >= h - 2:
                break
            if not label:
                y += 1
                continue
            line = f"  {label:<22s} \u2502 {value}"
            attr = curses.A_NORMAL
            if label == "Tracked" and ship.tracked:
                attr = curses.color_pair(3) | curses.A_BOLD
            self._put(y, 0, line[:w], attr)
            y += 1

        y += 1
        sep = f"\u2500 Recent Messages for MMSI {ship.mmsi} "
        sep += "\u2500" * max(0, w - len(sep))
        if y < h - 1:
            self._put(y, 0, sep[:w], curses.color_pair(7) | curses.A_BOLD)
        y += 1

        ship_msgs = [m for m in self._get_msgs() if m.mmsi == ship.mmsi]
        for msg in ship_msgs[-(h - y - 1):]:
            if y >= h - 1:
                break
            self._put(y, 0, msg.format(w)[:w])
            y += 1

        pause_hint = " Space:\u25b6Resume" if self.paused else " Space:\u23f8Pause"
        self._put(
            h - 1, 0,
            f" D/Esc:Back \u2502 T:Toggle Track \u2502{pause_hint}".ljust(w)[:w],
            curses.color_pair(1),
        )


def main():
    parser = argparse.ArgumentParser(
        description="AIS Monitor \u2014 btop-like TUI for real-time AIS traffic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"AIS TCP host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"AIS TCP port (default: {DEFAULT_PORT})")
    args = parser.parse_args()

    store = DataStore()
    rx = Receiver(store, args.host, args.port)
    rx.start()

    try:
        curses.wrapper(lambda scr: App(scr, store, args.host, args.port).run())
    finally:
        rx.running = False


if __name__ == "__main__":
    main()
