import json
import logging
import os
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock

from lockable.provider import Provider, ProviderError
from lockable.provider_list import ProviderList
from lockable.provider_http import ProviderHttp
from lockable.provider_file import ProviderFile
from lockable.provider_helpers import create as create_provider
import httptest


class TestHTTPServer200(httptest.Handler):

    def do_GET(self):
        contents = "[{\"id\": \"abc\"}]".encode()
        self.send_response(200)
        self.send_header("ETag", "1234567890")
        self.send_header("Last-Modified", "Mon, 01 Jan 1970 00:00:00 GMT")
        self.send_header("Content-type", "text/json")
        self.send_header("Content-length", len(contents))
        self.end_headers()
        self.wfile.write(contents)


class TestHTTPServer429(httptest.Handler):

    statuses = [429, 429, 200]
    call = 0

    def do_GET(self):
        contents = "[{\"id\": \"abc\"}]".encode()
        self.send_response(self.statuses[TestHTTPServer429.call % len(self.statuses)])
        TestHTTPServer429.call += 1
        self.send_header("ETag", "1234567890")
        self.send_header("Last-Modified", "Mon, 01 Jan 1970 00:00:00 GMT")
        self.send_header("Content-type", "text/json")
        self.send_header("Content-length", len(contents))
        self.end_headers()
        self.wfile.write(contents)


class TestHTTPServer404(httptest.Handler):

    def do_GET(self):
        contents = "[{\"id\": \"abc\"}]".encode()
        self.send_response(404)
        self.send_header("ETag", "1234567890")
        self.send_header("Last-Modified", "Mon, 01 Jan 1970 00:00:00 GMT")
        self.send_header("Content-type", "text/json")
        self.send_header("Content-length", len(contents))
        self.end_headers()
        self.wfile.write(contents)


class TestHTTPServerInvalidData(httptest.Handler):

    def do_GET(self):
        contents = "oh nou".encode()
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.send_header("Content-length", len(contents))
        self.end_headers()
        self.wfile.write(contents)


class ProviderTests(TestCase):
    def setUp(self) -> None:
        logger = logging.getLogger('lockable')
        logger.handlers.clear()
        logger.addHandler(logging.NullHandler())
        # backup
        self._total_retries = ProviderHttp.TOTAL_RETRIES
        self._backoff_factor = ProviderHttp.BACKOFF_FACTOR

    def tearDown(self) -> None:
        # restore
        ProviderHttp.TOTAL_RETRIES = self._total_retries
        ProviderHttp.BACKOFF_FACTOR = self._backoff_factor

    def test_create_raises(self):
        with self.assertRaises(FileNotFoundError):
            create_provider('file')
        with self.assertRaises(AssertionError):
            create_provider(object())

    def test_duplicate_id(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": "1"}, {"id":  "1"}]')
            with self.assertRaises(ValueError):
                create_provider(list_file)

    def test_create_success(self):
        self.assertIsInstance(create_provider([]), ProviderList)
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[]')
            self.assertIsInstance(create_provider(list_file), ProviderFile)

    def test_provider_list(self):
        with self.assertRaises(ValueError):
            create_provider([{}])
        provider = create_provider([])
        self.assertEqual(provider.data, [])

    def test_provider_list_set(self):
        provider = create_provider([])
        ref = {"id": "abc"}
        provider.set_resources_list([ref])
        self.assertDictEqual(provider.data[0], ref)

    def test_provider_file(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            ref = {"id": "abc"}
            with open(list_file, 'w') as fp:
                fp.write(json.dumps([ref]))
            provider = create_provider(list_file)
            self.assertDictEqual(provider.data[0], ref)

    @httptest.Server(TestHTTPServer200)
    def test_provider_http_success(self, ts=httptest.NoServer()):
        ts.server_name = 'localhost'
        provider = create_provider(ts.url())
        self.assertIsInstance(provider, ProviderHttp)
        self.assertEqual(len(provider.data), 1)
        self.assertDictEqual(provider.data[0], {"id": "abc"})

    @httptest.Server(TestHTTPServer404)
    def test_provider_http_not_found(self, ts=httptest.NoServer()):
        ts.server_name = 'localhost'
        with self.assertRaises(ProviderError):
            create_provider(ts.url())

    @httptest.Server(TestHTTPServerInvalidData)
    def test_provider_http_invalid_data(self, ts=httptest.NoServer()):
        ts.server_name = 'localhost'
        with self.assertRaises(ProviderError):
            create_provider(ts.url())

    @httptest.Server(TestHTTPServer429)
    def test_provider_http_too_many_requests_eventually_success(self, ts=httptest.NoServer()):
        ts.server_name = 'localhost'
        create_provider(ts.url())

    @httptest.Server(TestHTTPServer429)
    def test_provider_http_too_many_requests_fails(self, ts=httptest.NoServer()):
        ts.server_name = 'localhost'
        create_provider(ts.url())
        ProviderHttp.TOTAL_RETRIES = 2
        ProviderHttp.BACKOFF_FACTOR = 0
        with self.assertRaises(ProviderError):
            create_provider('http://localhost/resource')

    def test_provider_http_no_response(self):
        ProviderHttp.TOTAL_RETRIES = 2
        ProviderHttp.BACKOFF_FACTOR = 0
        with self.assertRaises(ProviderError):
            create_provider('http://localhost/resource')
