import os
import sys
import pathlib
import subprocess
import unittest

KEYWORDS_TO_IGNORE = (
    'bench',
    'tcp',
    'udp',
    'live',
    'tracking',
    'filters',
)


class TestExamples(unittest.TestCase):
    """
    Make sure that every example still runs - expect UDP and TCP examples as they require a socket
    """

    def test_run_every_file(self):
        i = -1
        exe = sys.executable
        for i, file in enumerate(pathlib.Path(__file__).parent.parent.joinpath('examples').glob('*.py')):
            if all(kw not in str(file) for kw in KEYWORDS_TO_IGNORE):
                env = os.environ
                env['PYTHONPATH'] = f':{pathlib.Path(__file__).parent.parent.absolute()}'
                assert subprocess.check_call(f'{exe} {file}'.split(), env=env, shell=False) == 0

        # Delete the file that was created by one of the tests
        csv_file = pathlib.Path("decoded_message.csv")
        if csv_file.exists():
            csv_file.unlink()

        assert i == 24
