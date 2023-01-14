import time
import unittest

from pyais.tracker import AISTracker, poplast
from pyais.messages import AISSentence


class TrackerTestCase(unittest.TestCase):

    def test_that_n_latest_returns_tracks_in_correct_order(self):
        tracker = AISTracker(ttl_in_seconds=None)

        # 227006760
        msg = AISSentence(b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23")
        tracker.update(msg, 1673259271.0)

        # 205448890
        msg = AISSentence(b"!AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F")
        tracker.update(msg, 1673259271.0)

        # 786434
        msg = AISSentence(b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B")
        tracker.update(msg, 1673259271.0)

        # 366913120
        msg = AISSentence(b"!AIVDM,1,1,,A,15MrVH0000KH<:V:NtBLoqFP2H9:,0*2F")
        tracker.update(msg, 1673259273.0)

        # 316013198
        msg = AISSentence(b"!AIVDM,1,1,,A,14eGrSPP00ncMJTO5C6aBwvP2D0?,0*7A")
        tracker.update(msg, 1673259272.0)

        # 249191000
        msg = AISSentence(b"!AIVDM,1,1,,B,13eaJF0P00Qd388Eew6aagvH85Ip,0*45")
        tracker.update(msg, 1673259271.0)

        # These latest three tracks MUST BE returned sorted by timestamp and NOT in insertion order
        latest_n = tracker.n_latest_tracks(3)
        assert [x.mmsi for x in latest_n] == [366913120, 316013198, 249191000]

        msg = AISSentence(b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23")
        tracker.update(msg, 1673259272.1)

        # The above message is younger than all other messages, except the youngest.
        # The latter MUST still be on top of all other messages.
        latest_n = tracker.n_latest_tracks(3)
        self.assertEqual([x.mmsi for x in latest_n], [366913120, 227006760, 316013198])

        # Once the youngest message is deleted, the next three messages should be returned
        tracker.pop_track(366913120)
        latest_n = tracker.n_latest_tracks(3)
        self.assertEqual([x.mmsi for x in latest_n], [227006760, 316013198, 249191000])

        # When all tracks are removed, this should return an empty list
        for track in tracker.tracks:
            tracker.pop_track(track.mmsi)
        latest_n = tracker.n_latest_tracks(3)
        self.assertEqual(latest_n, [])

    def test_that_n_latest_returns_empty_list_for_empty(self):
        tracker = AISTracker()
        latest_n = tracker.n_latest_tracks(3)
        self.assertEqual(latest_n, [])

    def test_that_tracker_works_as_context_manager(self):
        with AISTracker() as tracker:
            self.assertEqual(tracker.tracks, [])

    def test_that_tracks_property_returns_tracks_as_list(self):
        tracker = AISTracker(ttl_in_seconds=None)

        msg = AISSentence(b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23")
        tracker.update(msg, 1673259271.0)

        msg = AISSentence(b"!AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F")
        tracker.update(msg, 1673259271.0)

        msg = AISSentence(b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B")
        tracker.update(msg, 1673259271.0)

        self.assertEqual(len(tracker.tracks), 3)

    def test_that_update_always_updates_all_fields(self):
        msg = AISSentence(b"!AIVDO,1,1,,A,1U?MbV0003PecbBN`ja@0?w42000,0*58")
        tracker = AISTracker(ttl_in_seconds=None)
        tracker.update(msg, 1673259271.0)

        track = tracker.tracks[0]
        self.assertEqual(len(tracker.tracks), 1)
        self.assertEqual(track.mmsi, 351759000)
        self.assertEqual(track.course, 0.0)
        self.assertEqual(track.heading, 511)
        self.assertEqual(track.lat, 53.542675)
        self.assertEqual(track.lon, 9.979428)
        self.assertEqual(track.speed, 0.3)
        self.assertEqual(track.shipname, None)
        self.assertEqual(track.ship_type, None)
        self.assertEqual(track.destination, None)

        msg = AISSentence(b"!AIVDO,1,1,,A,1U?MbV000?Peid0;LK000?w42000,0*73")
        tracker.update(msg, 1673259271.1)

        track = tracker.tracks[0]
        self.assertEqual(len(tracker.tracks), 1)
        self.assertEqual(track.mmsi, 351759000)
        self.assertEqual(track.course, 0.0)
        self.assertEqual(track.heading, 511)
        self.assertEqual(track.lat, 20.00000)
        self.assertEqual(track.lon, 10.00000)
        self.assertEqual(track.speed, 1.5)
        self.assertEqual(track.shipname, None)
        self.assertEqual(track.ship_type, None)
        self.assertEqual(track.destination, None)

        msg = AISSentence.assemble_from_iterable([
            AISSentence(b"!AIVDM,2,1,0,B,55?MbV02;H;s<HtKP00EHE:0@T4@Dl0000000000L961O5Gf0NSQEp6ClRh0,0*0B"),
            AISSentence(b"!AIVDM,2,2,0,B,00000000000,2*27"),
        ])
        tracker.update(msg, 1673259271.2)

        track = tracker.tracks[0]
        self.assertEqual(len(tracker.tracks), 1)
        self.assertEqual(track.mmsi, 351759000)
        self.assertEqual(track.course, 0.0)
        self.assertEqual(track.heading, 511)
        self.assertEqual(track.lat, 20.00000)
        self.assertEqual(track.lon, 10.00000)
        self.assertEqual(track.speed, 1.5)
        self.assertEqual(track.shipname, 'EVER DIADEM')
        self.assertEqual(track.ship_type, 0)
        self.assertEqual(track.destination, 'NEW YORK')

    def test_that_update_raises_error_is_timestamp_is_younger(self):
        msg = AISSentence(b"!AIVDO,1,1,,A,1U?MbV0003PecbBN`ja@0?w42000,0*58")
        tracker = AISTracker(ttl_in_seconds=None)
        tracker.update(msg, 1673259271.0)

        with self.assertRaises(ValueError):
            tracker.update(msg, 1673259270.0)

    def test_that_update_cleans_up_afterwards(self):
        msg = AISSentence(b"!AIVDO,1,1,,A,1U?MbV0003PecbBN`ja@0?w42000,0*58")
        tracker = AISTracker(ttl_in_seconds=5)
        tracker.update(msg, 1673259271.0)
        self.assertEqual(tracker.tracks, [])

        tracker.update(msg, time.time())
        self.assertEqual(len(tracker.tracks), 1)

    def test_that_get_track_returns_track_if_it_exists(self):
        msg = AISSentence(b"!AIVDO,1,1,,A,1U?MbV0003PecbBN`ja@0?w42000,0*58")
        tracker = AISTracker(ttl_in_seconds=None)
        tracker.update(msg, 1673259271.0)

        self.assertEqual(tracker.get_track(351759000).mmsi, 351759000)
        self.assertEqual(tracker.get_track(351759001), None)

    def test_that_pop_tracks_returns_and_deletes_track_if_it_exists(self):
        msg = AISSentence(b"!AIVDO,1,1,,A,1U?MbV0003PecbBN`ja@0?w42000,0*58")
        tracker = AISTracker(ttl_in_seconds=None)
        tracker.update(msg, 1673259271.0)

        self.assertEqual(tracker.pop_track(351759000).mmsi, 351759000)
        self.assertEqual(tracker.pop_track(351759001), None)

    def test_that_insert_or_update_sets_oldest_timestamp(self):
        tracker = AISTracker(ttl_in_seconds=None)

        self.assertEqual(tracker.oldest_timestamp, None)

        msg = AISSentence(b"!AIVDO,1,1,,A,1U?MbV0003PecbBN`ja@0?w42000,0*58")
        tracker.update(msg, 1673259271.0)
        self.assertEqual(tracker.oldest_timestamp, 1673259271)

        msg = AISSentence(b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B")
        tracker.update(msg, 1673259250.0)
        self.assertEqual(tracker.oldest_timestamp, 1673259250)

    def test_that_clean_up_does_nothing_if_ttl_is_none(self):
        msg = AISSentence(b"!AIVDO,1,1,,A,1U?MbV0003PecbBN`ja@0?w42000,0*58")
        tracker = AISTracker(ttl_in_seconds=None)
        tracker.update(msg, 1673259271.0)
        tracker.cleanup()
        self.assertEqual(len(tracker.tracks), 1)

        tracker.ttl_in_seconds = 1
        tracker.cleanup()
        self.assertEqual(len(tracker.tracks), 0)

    def test_that_clean_up_deletes_tracks_if_they_expire(self):
        tracker = AISTracker(ttl_in_seconds=3)

        now = time.time()

        # 227006760
        msg = AISSentence(b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23")
        tracker.update(msg, now - 4)

        # 205448890
        msg = AISSentence(b"!AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F")
        tracker.update(msg, now - 3)

        # 786434
        msg = AISSentence(b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B")
        tracker.update(msg, now - 2)

        # 366913120
        msg = AISSentence(b"!AIVDM,1,1,,A,15MrVH0000KH<:V:NtBLoqFP2H9:,0*2F")
        tracker.update(msg, now - 2)

        # 316013198
        msg = AISSentence(b"!AIVDM,1,1,,A,14eGrSPP00ncMJTO5C6aBwvP2D0?,0*7A")
        tracker.update(msg, now - 1)

        # 249191000
        msg = AISSentence(b"!AIVDM,1,1,,B,13eaJF0P00Qd388Eew6aagvH85Ip,0*45")
        tracker.update(msg, now)

        self.assertEqual(len(tracker.tracks), 4)

    def test_that_ordered_tracker_handles_cleanup(self):
        tracker = AISTracker(ttl_in_seconds=None, stream_is_ordered=True)
        now = time.time()

        # 227006760
        msg = AISSentence(b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23")
        tracker.update(msg, now - 4)

        # 205448890
        msg = AISSentence(b"!AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F")
        tracker.update(msg, now - 3)

        # 786434
        msg = AISSentence(b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B")
        tracker.update(msg, now - 2)

        tracker.ttl_in_seconds = 3
        tracker.cleanup()
        self.assertEqual(len(tracker.tracks), 1)
        self.assertEqual(tracker.tracks[0].mmsi, 786434)

    def test_that_ordered_tracker_returns_correct_latest_n(self):
        tracker = AISTracker(ttl_in_seconds=None, stream_is_ordered=True)

        # 227006760
        msg = AISSentence(b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23")
        tracker.update(msg, 1673259271.0)

        # 205448890
        msg = AISSentence(b"!AIVDM,1,1,,A,133sVfPP00PD>hRMDH@jNOvN20S8,0*7F")
        tracker.update(msg, 1673259272.0)

        # 786434
        msg = AISSentence(b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B")
        tracker.update(msg, 1673259272.000001)

        latest_n = tracker.n_latest_tracks(5)
        self.assertEqual([x.mmsi for x in latest_n], [227006760, 205448890, 786434])
        self.assertEqual(list(tracker._tracks.keys()), [227006760, 205448890, 786434])

        # 227006760
        msg = AISSentence(b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23")
        tracker.update(msg, 1673259272.000001)

        latest_n = tracker.n_latest_tracks(5)
        self.assertEqual([x.mmsi for x in latest_n], [205448890, 786434, 227006760])
        self.assertEqual(list(tracker._tracks.keys()), [205448890, 786434, 227006760])

    def test_that_ordered_tracker_raises_value_error_if_older_record_is_received(self):
        tracker = AISTracker(ttl_in_seconds=None, stream_is_ordered=True)

        # 227006760
        msg = AISSentence(b"!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23")
        tracker.update(msg, 1673259271.0)

        # This should raise an error
        with self.assertRaises(ValueError) as err:
            tracker.update(msg, 1673259270.99)

        self.assertEqual(
            str(err.exception),
            'can not insert an older timestamp in a ordered stream. 1673259270.99 < 1673259271.0. consider setting stream_is_ordered to False.'
        )

        # This should raise an error also
        with self.assertRaises(ValueError) as err:
            msg = AISSentence(b"!AIVDM,1,1,,B,100h00PP0@PHFV`Mg5gTH?vNPUIp,0*3B")
            tracker.update(msg, 1673259270.0)

        self.assertEqual(
            str(err.exception),
            'can not insert an older timestamp in a ordered stream. 1673259270.0 < 1673259271.0. consider setting stream_is_ordered to False.'
        )

    def test_that_poplast_is_non_destructive(self):
        d = {'a': 1337}
        i = poplast(d)

        self.assertEqual(d, {'a': 1337})
        self.assertEqual(i, 1337)

        d = {'a': 1337, 'foo': 'bar'}
        i = poplast(d)

        self.assertEqual(d, {'a': 1337, 'foo': 'bar'})
        self.assertEqual(i, 'bar')

        for _ in range(10):
            poplast(d)

        self.assertEqual(d, {'a': 1337, 'foo': 'bar'})
