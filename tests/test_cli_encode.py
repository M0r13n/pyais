#!/usr/bin/env python3
"""
Unit tests for AIS JSON to NMEA Encoder
"""

import unittest
from unittest.mock import patch
from io import StringIO
import json

from pyais.ais_encode import (
    AISJSONDecoder,
    create_parser,
    read_json_stream,
    read,
    main,
    KNOWN_FIELDS
)


class TestAISJSONDecoder(unittest.TestCase):
    """Test the custom JSON decoder that filters unknown fields"""

    def setUp(self):
        self.decoder = AISJSONDecoder()

    def test_filter_known_fields(self):
        """Test that only known fields are kept"""
        input_data = {
            'msg_type': 1,
            'mmsi': 123456789,
            'unknown_field': 'should_be_removed',
            'lat': 59.0,
            'invalid_key': 42
        }

        result = self.decoder.decode(json.dumps(input_data))
        expected = {
            'msg_type': 1,
            'mmsi': 123456789,
            'lat': 59.0
        }

        self.assertEqual(result, expected)
        self.assertNotIn('unknown_field', result)
        self.assertNotIn('invalid_key', result)

    def test_empty_object(self):
        """Test handling of empty JSON object"""
        result = self.decoder.decode('{}')
        self.assertEqual(result, {})

    def test_all_unknown_fields(self):
        """Test object with only unknown fields"""
        input_data = {
            'completely_unknown': 'value',
            'another_unknown': 123
        }

        result = self.decoder.decode(json.dumps(input_data))
        self.assertEqual(result, {})


class TestCreateParser(unittest.TestCase):
    """Test argument parser creation and validation"""

    def setUp(self):
        self.parser = create_parser()

    def test_default_arguments(self):
        """Test default argument values"""
        args = self.parser.parse_args([])

        self.assertEqual(args.mode, 'auto')
        self.assertEqual(args.talker, 'AIVDM')
        self.assertEqual(args.radio, 'A')

    def test_mode_choices(self):
        """Test valid mode choices"""
        valid_modes = ['single', 'lines', 'stream', 'auto']

        for mode in valid_modes:
            args = self.parser.parse_args(['--mode', mode])
            self.assertEqual(args.mode, mode)

    def test_invalid_mode(self):
        """Test invalid mode raises SystemExit"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--mode', 'invalid'])

    def test_talker_choices(self):
        """Test talker ID choices and case conversion"""
        # Test uppercase
        args = self.parser.parse_args(['--talker', 'AIVDO'])
        self.assertEqual(args.talker, 'AIVDO')

        # Test lowercase conversion
        args = self.parser.parse_args(['--talker', 'aivdo'])
        self.assertEqual(args.talker, 'AIVDO')

    def test_radio_choices(self):
        """Test radio channel choices and case conversion"""
        # Test uppercase
        args = self.parser.parse_args(['--radio', 'B'])
        self.assertEqual(args.radio, 'B')

        # Test lowercase conversion
        args = self.parser.parse_args(['--radio', 'b'])
        self.assertEqual(args.radio, 'B')

    def test_invalid_talker(self):
        """Test invalid talker raises SystemExit"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--talker', 'INVALID'])

    def test_invalid_radio(self):
        """Test invalid radio channel raises SystemExit"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--radio', 'C'])


class TestReadJsonStream(unittest.TestCase):
    """Test streaming JSON reader"""

    def test_single_complete_object(self):
        """Test reading a single complete JSON object"""
        input_data = '{"msg_type": 1, "mmsi": 123456789}\n'
        file_obj = StringIO(input_data)

        results = list(read_json_stream(file_obj))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], {"msg_type": 1, "mmsi": 123456789})

    def test_multiple_objects_single_line(self):
        """Test reading multiple JSON objects on single line"""
        input_data = '{"msg_type": 1}{"msg_type": 2}\n'
        file_obj = StringIO(input_data)

        results = list(read_json_stream(file_obj))

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {"msg_type": 1})
        self.assertEqual(results[1], {"msg_type": 2})

    def test_objects_across_multiple_lines(self):
        """Test reading objects split across lines"""
        input_data = '{"msg_type": 1,\n"mmsi": 123456789}\n'
        file_obj = StringIO(input_data)

        results = list(read_json_stream(file_obj))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], {"msg_type": 1, "mmsi": 123456789})

    def test_empty_input(self):
        """Test handling empty input"""
        file_obj = StringIO('')

        results = list(read_json_stream(file_obj))

        self.assertEqual(len(results), 0)

    def test_whitespace_handling(self):
        """Test proper whitespace handling"""
        input_data = '  \n  {"msg_type": 1}  \n  '
        file_obj = StringIO(input_data)

        results = list(read_json_stream(file_obj))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], {"msg_type": 1})


class TestRead(unittest.TestCase):
    """Test the main read function with different modes"""

    @patch('pyais.ais_encode.sys.stdin')
    def test_read_single_mode(self, mock_stdin):
        """Test single mode reading"""
        mock_stdin.read.return_value = '{"msg_type": 1, "mmsi": 123456789}'

        results = list(read('single'))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], {"msg_type": 1, "mmsi": 123456789})

    @patch('pyais.ais_encode.sys.stdin')
    def test_read_lines_mode(self, mock_stdin):
        """Test lines mode reading"""
        mock_stdin.read.return_value = '{"msg_type": 1}\n{"msg_type": 2}\n'

        results = list(read('lines'))

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {"msg_type": 1})
        self.assertEqual(results[1], {"msg_type": 2})

    @patch('pyais.ais_encode.sys.stdin')
    def test_read_lines_mode_with_empty_lines(self, mock_stdin):
        """Test lines mode with empty lines"""
        mock_stdin.read.return_value = '{"msg_type": 1}\n\n{"msg_type": 2}\n\n'

        results = list(read('lines'))

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {"msg_type": 1})
        self.assertEqual(results[1], {"msg_type": 2})

    @patch('pyais.ais_encode.read_json_stream')
    @patch('pyais.ais_encode.sys.stdin')
    def test_read_stream_mode(self, mock_stdin, mock_stream):
        """Test stream mode delegates to read_json_stream"""
        mock_stream.return_value = [{"msg_type": 1}]

        results = list(read('stream'))

        mock_stream.assert_called_once_with(mock_stdin)
        self.assertEqual(results, [{"msg_type": 1}])

    @patch('pyais.ais_encode.sys.stdin')
    def test_read_auto_mode_single_object(self, mock_stdin):
        """Test auto mode with single JSON object"""
        mock_stdin.read.return_value = '{"msg_type": 1, "mmsi": 123456789}'

        results = list(read('auto'))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], {"msg_type": 1, "mmsi": 123456789})

    @patch('pyais.ais_encode.sys.stdin')
    def test_read_auto_mode_fallback_to_lines(self, mock_stdin):
        """Test auto mode fallback to line-delimited"""
        mock_stdin.read.return_value = '{"msg_type": 1}\n{"msg_type": 2}'

        results = list(read('auto'))

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {"msg_type": 1})
        self.assertEqual(results[1], {"msg_type": 2})

    @patch('pyais.ais_encode.sys.stdin')
    def test_read_empty_input(self, mock_stdin):
        """Test handling of empty input"""
        mock_stdin.read.return_value = ''

        results = list(read('single'))

        self.assertEqual(len(results), 0)

    @patch('pyais.ais_encode.sys.stdin')
    def test_read_whitespace_only_input(self, mock_stdin):
        """Test handling of whitespace-only input"""
        mock_stdin.read.return_value = '   \n  \t  '

        results = list(read('single'))

        self.assertEqual(len(results), 0)


class TestMain(unittest.TestCase):
    """Test the main function"""

    @patch('pyais.ais_encode.encode_dict')
    @patch('pyais.ais_encode.read')
    @patch('pyais.ais_encode.sys.argv', ['ais-encode'])
    @patch('pyais.ais_encode.sys.stdout', new_callable=StringIO)
    def test_main_success(self, mock_stdout, mock_read, mock_encode):
        """Test successful encoding and output"""
        mock_read.return_value = [{"msg_type": 1, "mmsi": 123456789}]
        mock_encode.return_value = ["!AIVDM,1,1,,A,15M:@d001H@Hb4,0*56"]

        result = main()

        self.assertEqual(result, 0)
        mock_encode.assert_called_once_with(
            {"msg_type": 1, "mmsi": 123456789},
            talker_id='AIVDM',
            radio_channel='A'
        )
        output = mock_stdout.getvalue()
        self.assertIn("!AIVDM,1,1,,A,15M:@d001H@Hb4,0*56", output)

    @patch('pyais.ais_encode.encode_dict')
    @patch('pyais.ais_encode.read')
    @patch('pyais.ais_encode.sys.argv', ['ais-encode', '--talker', 'AIVDO', '--radio', 'B'])
    @patch('pyais.ais_encode.sys.stdout', new_callable=StringIO)
    def test_main_with_custom_args(self, mock_stdout, mock_read, mock_encode):
        """Test main with custom talker and radio arguments"""
        mock_read.return_value = [{"msg_type": 1, "mmsi": 123456789}]
        mock_encode.return_value = ["!AIVDO,1,1,,B,15M:@d001H@Hb4,0*56"]

        result = main()

        self.assertEqual(result, 0)
        mock_encode.assert_called_once_with(
            {"msg_type": 1, "mmsi": 123456789},
            talker_id='AIVDO',
            radio_channel='B'
        )

    @patch('pyais.ais_encode.encode_dict')
    @patch('pyais.ais_encode.read')
    @patch('pyais.ais_encode.sys.argv', ['ais-encode'])
    @patch('pyais.ais_encode.sys.stderr', new_callable=StringIO)
    def test_main_encoding_error(self, mock_stderr, mock_read, mock_encode):
        """Test handling of encoding errors"""
        mock_read.return_value = [{"msg_type": 1, "mmsi": 123456789}]
        mock_encode.side_effect = ValueError("Invalid message type")

        result = main()

        self.assertEqual(result, 0)  # Should continue processing
        error_output = mock_stderr.getvalue()
        self.assertIn("Failed to encode: Invalid message type", error_output)

    @patch('pyais.ais_encode.read')
    @patch('pyais.ais_encode.sys.argv', ['ais-encode'])
    @patch('pyais.ais_encode.sys.stderr', new_callable=StringIO)
    def test_main_json_decode_error(self, mock_stderr, mock_read):
        """Test handling of JSON decode errors"""
        mock_read.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        result = main()

        self.assertEqual(result, 1)
        error_output = mock_stderr.getvalue()
        self.assertIn("Error parsing JSON", error_output)

    @patch('pyais.ais_encode.read')
    @patch('pyais.ais_encode.sys.argv', ['ais-encode'])
    @patch('pyais.ais_encode.sys.stderr', new_callable=StringIO)
    def test_main_value_error(self, mock_stderr, mock_read):
        """Test handling of value errors"""
        mock_read.side_effect = ValueError("Invalid value")

        result = main()

        self.assertEqual(result, 1)
        error_output = mock_stderr.getvalue()
        self.assertIn("Error parsing JSON", error_output)

    @patch('pyais.ais_encode.encode_dict')
    @patch('pyais.ais_encode.read')
    @patch('pyais.ais_encode.sys.argv', ['ais-encode'])
    @patch('pyais.ais_encode.sys.stdout', new_callable=StringIO)
    def test_main_multiple_messages(self, mock_stdout, mock_read, mock_encode):
        """Test processing multiple messages"""
        mock_read.return_value = [
            {"msg_type": 1, "mmsi": 123456789},
            {"msg_type": 2, "mmsi": 987654321}
        ]
        mock_encode.side_effect = [
            ["!AIVDM,1,1,,A,15M:@d001H@Hb4,0*56"],
            ["!AIVDM,1,1,,A,25M:@d001H@Hb4,0*57"]
        ]

        result = main()

        self.assertEqual(result, 0)
        self.assertEqual(mock_encode.call_count, 2)
        output = mock_stdout.getvalue()
        self.assertEqual(output.count('\n'), 2)  # Two lines of output


class TestKnownFields(unittest.TestCase):
    """Test the KNOWN_FIELDS constant"""

    def test_known_fields_is_set(self):
        """Test that KNOWN_FIELDS is a set for O(1) lookup"""
        self.assertIsInstance(KNOWN_FIELDS, set)

    def test_known_fields_contains_essential_fields(self):
        """Test that essential AIS fields are included"""
        essential_fields = {'msg_type', 'mmsi', 'lat', 'lon', 'speed', 'course'}

        for field in essential_fields:
            self.assertIn(field, KNOWN_FIELDS, f"Essential field '{field}' missing from KNOWN_FIELDS")

    def test_known_fields_not_empty(self):
        """Test that KNOWN_FIELDS is not empty"""
        self.assertGreater(len(KNOWN_FIELDS), 0)


if __name__ == '__main__':
    unittest.main()
