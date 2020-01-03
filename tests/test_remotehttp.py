import unittest
from mdlg.persistence.remoteHttp import Galactica
from unittest.mock import patch
import json


class FakeReqOpener:
    def __enter__(self):
        return self
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def read(self):
        return json.dumps({
            "profile": "http://library.stanford.edu/iiif/image-api/1.1/compliance.html#level2",
            "width": 100,
            "height": 200,
            "@context": "http://library.stanford.edu/iiif/image-api/1.1/context.json",
            "@id": "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11"
        })


class TestRemoteHTTP(unittest.TestCase):
    @patch('mdlg.persistence.remoteHttp.urllib.request.urlopen')
    def test_collect_image_size(self, mock_urlopen):
        mock_urlopen.return_value = FakeReqOpener()

        width, height = Galactica.collect_image_size("https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11/info.json")
        self.assertEqual(100, width)
        self.assertEqual(200, height)
