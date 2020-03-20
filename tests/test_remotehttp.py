import unittest
from mdlg.persistence.remoteHttp import download_binary_file, GalacticaSession
from unittest.mock import patch
import tempfile
import os
from requests import Session
from mdlg.model.model import GalacticaURL


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
    @patch('mdlg.persistence.remoteHttp.requests.Session.get')
    def test_collect_image_size(self, mock_requests):
        mock_requests.return_value = FakeRequest()

        with GalacticaSession() as g:
            width, height = g.collect_image_size("https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11/info.json")
        self.assertEqual(100, width)
        self.assertEqual(200, height)

    def test_download_file(self):
        FILENAME = "google_home.http"
        with tempfile.TemporaryDirectory() as tmpdir:
            datafile = os.path.join(tmpdir, FILENAME)
            with Session() as s:
                download_binary_file(s, "http://www.google.com", datafile)

            self.assertTrue(os.path.getsize(datafile) > 10, "dowmloaded file has length below 10 bytes")
            with open(datafile, 'rb') as d:
                s = d.read()
                self.assertTrue(s.find(bytes("html", "ascii")) > 0, "cannot retrieve the tag htmml in google's homepage")


class TestGalacticaSession(unittest.TestCase):
    @unittest.skip("we do not ant to download from BNF on each UT")
    def test_download_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            datafile = os.path.join(tmpdir, "data-gallica_847020_f11.json")
            gal = GalacticaURL.from_url("https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11").set_zone('full').set_rotation(0).set_size(10).set_quality(
                'native').set_file_format('jpg')
            with GalacticaSession() as g:
                g.download_image(gal.as_url(), datafile)
                w, h = g.collect_image_size(gal.as_url())
