import os
import pathlib
import subprocess
import unittest


class TestExamples(unittest.TestCase):
    """
    Make sure that every example still runs - expect UDP and TCP examples as they require a socket
    """

    def test_run_every_file(self):
        i = -1
        for i, file in enumerate(pathlib.Path(__file__).parent.parent.joinpath('examples').glob('*.py')):
            if 'tcp' not in str(file) and 'udp' not in str(file):
                env = os.environ
                env['PYTHONPATH'] = f':{pathlib.Path(__file__).parent.parent.absolute()}'
                assert subprocess.check_call(f'python3 {file}'.split(), env=env, shell=False) == 0

        assert i == 7
