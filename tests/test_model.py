from mdlg.model.model import GalacticaURL, ZONE_FULL, ZONE_KEYS, SIZE_FULL, SIZE_KEYS
import unittest


class TestGalacticaURL(unittest.TestCase):
    # valid URL = https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11/398,195,2317,3945/full/0/native.jpg-1
    def test_valid_url(self):
        url = "https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/11,12,13,14/full/0/native.jpg-1"
        gal = GalacticaURL.from_url(url)

        self.assertTrue(gal.is_valid(), 'url {0} expected to be true'.format(url))
        self.assertEqual("DOCUMENTID", gal.document_id())
        self.assertEqual(200, gal.page_number())
        self.assertEqual({'x': 11, 'y': 12, 'width': 13, 'height': 14}, gal.zone())
        self.assertEqual('DOCUMENTID_200', gal.as_filename())
        self.assertEqual("https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/info.json", gal.url_image_properties().as_url())
        self.assertEqual("https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/full/full/0/native.jpg-1", gal.set_zone().as_url())
        self.assertEqual("https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/full/full/0/native.jpg-1", gal.set_zone(None).as_url())
        self.assertEqual("https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/full/full/0/native.jpg-1", gal.set_zone(ZONE_FULL).as_url())
        self.assertEqual("https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/1,2,3,4/full/0/native.jpg-1", gal.set_zone((1, 2, 3, 4)).as_url())
        self.assertEqual("https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/1,2,3,4/full/0/native.jpg-1",
                         gal.set_zone((1, 2, 3, 4)).set_size(None).as_url())
        self.assertEqual("https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/1,2,3,4/full/0/native.jpg-1",
                         gal.set_zone((1, 2, 3, 4)).set_size(SIZE_FULL).as_url())
        self.assertEqual("https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/1,2,3,4/20,40/0/native.jpg-1",
                         gal.set_zone((1, 2, 3, 4)).set_size((20, 40)).as_url())
        self.assertEqual("https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/11,12,13,14/full/90/native.jpg-1", gal.set_rotation(90).as_url())
        self.assertEqual("https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/11,12,13,14/full/0/bicolor.jpg-1", gal.set_quality('bicolor').as_url())
        self.assertEqual("https://gallica.bnf.fr/iiif/ark:/12148/btv1bDOCUMENTIDd/f200/11,12,13,14/full/0/bicolor.png",
                         gal.set_quality('bicolor').set_file_format('png').as_url())
