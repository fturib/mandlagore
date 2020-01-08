import unittest
from mdlg.persistence.remoteHttp import Galactica, download_binary_file
from unittest.mock import patch
import json
import tempfile
import os


class FakeRequest:
    def raise_for_status(self):
        pass

    def json(self):
        return ({
            "profile": "http://library.stanford.edu/iiif/image-api/1.1/compliance.html#level2",
            "width": 100,
            "height": 200,
            "@context": "http://library.stanford.edu/iiif/image-api/1.1/context.json",
            "@id": "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11"
        })


class TestRemoteHTTP(unittest.TestCase):
    @patch('mdlg.persistence.remoteHttp.requests.get')
    def test_collect_image_size(self, mock_requests):
        mock_requests.return_value = FakeRequest()

        width, height = Galactica.collect_image_size("https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11/info.json")
        self.assertEqual(100, width)
        self.assertEqual(200, height)

    def test_download_file(self):
        FILENAME = "google_home.http"
        with tempfile.TemporaryDirectory() as tmpdir:
            datafile = os.path.join(tmpdir, "data-gallica_12148_f11.json")
            download_binary_file("http://www.google.com", FILENAME)
            
            self.assertTrue(os.path.getsize(FILENAME) > 10, "dowmloaded file has length below 10 bytes")
            s = open(FILENAME, 'rb').read()
            self.assertTrue(s.find(bytes("html", "ascii")) > 0, "cannot retrieve the tag htmml in google's homepage")



