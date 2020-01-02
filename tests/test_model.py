from mdlg.model.model import GalacticaURL
import unittest


class TestGalacticaURL(unittest.TestCase):
    # valid URL = https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11/398,195,2317,3945/full/0/native.jpg-1
    def test_valid_url(self):
        url = "https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/1,2,3,4/full/0/native.jpg-1"
        gal = GalacticaURL(url)

        self.assertTrue(gal.is_valid(), 'url {0} expected to be true'.format(url))
        self.assertEqual("DOCUMENTID", gal.document_id())
        self.assertEqual(200, gal.page_number())
        self.assertEqual({'x': 1, 'y': 2, 'width': 3, 'height': 4}, gal.size_px())
        self.assertEqual('DOCUMENTID_200', gal.as_filename())
        self.assertEqual("https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/info.json", gal.url_image_properties())

