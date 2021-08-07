import json
import logging
import os
from tempfile import TemporaryDirectory
from unittest import TestCase
from lockable.provider import Provider, ProviderError, ProviderList, ProviderHttp, ProviderFile
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

    def test_create_raises(self):
        with self.assertRaises(FileNotFoundError):
            Provider.create('file')
        with self.assertRaises(AssertionError):
            Provider.create(object())

    def test_duplicate_id(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[{"id": "1"}, {"id":  "1"}]')
            with self.assertRaises(ValueError):
                Provider.create(list_file)

    def test_create_success(self):
        self.assertIsInstance(Provider.create([]), ProviderList)
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            with open(list_file, 'w') as fp:
                fp.write('[]')
            self.assertIsInstance(Provider.create(list_file), ProviderFile)

    def test_provider_list(self):
        with self.assertRaises(ValueError):
            Provider.create([{}])
        provider = Provider.create([])
        self.assertEqual(provider.data, [])

    def test_provider_list_set(self):
        provider = Provider.create([])
        ref = {"id": "abc"}
        provider.set_resources_list([ref])
        self.assertDictEqual(provider.data[0], ref)

    def test_provider_file(self):
        with TemporaryDirectory() as tmpdirname:
            list_file = os.path.join(tmpdirname, 'test.json')
            ref = {"id": "abc"}
            with open(list_file, 'w') as fp:
                fp.write(json.dumps([ref]))
            provider = Provider.create(list_file)
            self.assertDictEqual(provider.data[0], ref)

    @httptest.Server(TestHTTPServer200)
    def test_provider_http_success(self, ts=httptest.NoServer()):
        ts.server_name = 'localhost'
        provider = Provider.create(ts.url())
        self.assertEqual(len(provider.data), 1)
        self.assertDictEqual(provider.data[0], {"id": "abc"})

    @httptest.Server(TestHTTPServer404)
    def test_provider_http_not_found(self, ts=httptest.NoServer()):
        ts.server_name = 'localhost'
        with self.assertRaises(ProviderError):
            Provider.create(ts.url())

    @httptest.Server(TestHTTPServerInvalidData)
    def test_provider_http_invalid_data(self, ts=httptest.NoServer()):
        ts.server_name = 'localhost'
        with self.assertRaises(ProviderError):
            Provider.create(ts.url())
