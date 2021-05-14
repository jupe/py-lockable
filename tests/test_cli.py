import os
import sys
import logging
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from lockable.cli import main


class LockableCliTests(TestCase):

    def setUp(self) -> None:
        logger = logging.getLogger('lockable')
        logger.handlers.clear()
        logger.addHandler(logging.NullHandler())

    def test_help(self):
        testargs = ["prog", "--help"]
        with self.assertRaises(SystemExit) as cm:
            with patch.object(sys, 'argv', testargs):
                main()
        self.assertEqual(cm.exception.code, 0)

    def test_missing_command(self):
        with TemporaryDirectory() as tmpdirname:
            testargs = ["prog"]
            with self.assertRaises(SystemExit) as cm:
                with patch.object(sys, 'argv', testargs):
                    main()
            self.assertEqual(cm.exception.code, 1)

    def test_host_not_found(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'resources.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": "abc", "hostname": "localhost", "online": true}]')
            testargs = ["prog", "--hostname", "localhost", "--resources", list_file, "echo", "$ID"]
            with self.assertRaises(SystemExit) as cm:
                with patch.object(sys, 'argv', testargs):
                    main()
            self.assertEqual(cm.exception.code, 0)

    def test_validate_only_fail(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'resources.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": "abc", "hostname": "localhost", "online": true},'
                         ' {"id": "abc", "hostname": "localhost2", "online": true}]')
            testargs = ["prog", "--validate-only", "--hostname", "localhost", "--resources", list_file, "echo", "$ID"]
            with self.assertRaises(ValueError):
                with patch.object(sys, 'argv', testargs):
                    main()

    def test_validate_only_ok(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'resources.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": "abc", "hostname": "localhost", "online": true}]')
            testargs = ["prog", "--validate-only", "--hostname", "localhost", "--resources", list_file, "echo", "$ID"]
            with self.assertRaises(SystemExit) as cm:
                with patch.object(sys, 'argv', testargs):
                    main()
            self.assertEqual(cm.exception.code, 0)
