from unittest import mock
import unittest
import os
from run_newwebserver import get_input
from run_newwebserver import import_key_pair


class TestFunctions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestFunctions, cls).setUpClass()
        filename = r"keys/key_pair.pem"
        # Create .pem file
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write("DAG#svcsds23daCWE$@F")

    @classmethod
    def tearDownClass(cls):
        super(TestFunctions, cls).tearDownClass()
        # Remove .pem file
        os.system("rm -rf ./keys")

    def test_get_input(self):
        with mock.patch('builtins.input', return_value='The quick brown fox jumps over the lazy dog'):
            self.assertEqual(input(), get_input('The quick brown fox jumps over the lazy dog'))

    def test_import_key_pair(self):
        with mock.patch('builtins.input', return_value=('key_pair', 'keys/key_pair.pem')):
            self.assertEqual(input(), import_key_pair('keys/key_pair.pem'))


if __name__ == '__main__':
    unittest.main()
