import unittest
import unittest.mock
import json
import tempfile
from mdlg.services.via_label_manager import ViaLabelManager
import os

gallica_12148_f11 = {
    "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11/398,195,2317,3945/full/0/native.jpg-1":
    {
        "filename":
        "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11/398,195,2317,3945/full/0/native.jpg",
        "size": -1,
        "regions": [
            {
                "shape_attributes": {
                    "name": "rect",
                    "x": 449,
                    "y": 1610,
                    "width": 1363,
                    "height": 1257
                },
                "region_attributes": {
                    "Descripteur": "armoiries",
                    "Type": "objet"
                }
            },
            {
                "shape_attributes": {
                    "name": "rect",
                    "x": 656,
                    "y": 122,
                    "width": 875,
                    "height": 568
                },
                "region_attributes": {
                    "Descripteur": "serpent",
                    "Type": "objet"
                }
            },
        ],
        "file_attributes": {
            "MandragoreId": "60106"
        },
    }
}

SCENES = [{
    'mandragoreID':
    'ID1',
    'documentURL':
    'https://gallica.bnf.fr/iiif/ark:/12148/doc/page1/5,5,10,40/full/0/native.jpg',
    'imageID':
    'doc-page1',
    'size': {
        'x': 1,
        'y': 1,
        'width': 100,
        'height': 200
    },
    'descriptors': [{
        'classID': 'dog',
        'location': {
            'x': 5,
            'y': 5,
            'width': 10,
            'height': 40
        }
    }]
}, {
    'mandragoreID':
    'ID2',
    'documentURL':
    'https://gallica.bnf.fr/iiif/ark:/12148/doc/page2/2,2,200,500/full/0/native.jpg',
    'imageID':
    'doc-page2',
    'size': {
        'x': 2,
        'y': 2,
        'width': 200,
        'height': 500
    },
    'descriptors': [{
        'classID': 'dog',
        'location': {
            'x': 50,
            'y': 50,
            'width': 20,
            'height': 100
        }
    }]
}]


class TestViaLabelManager(unittest.TestCase):
    def test_describe_one_scene(self):

        with tempfile.TemporaryDirectory() as tmpdir:
            datafile = os.path.join(tmpdir, "data-gallica_12148_f11.json")
            with open(datafile, 'w') as content_file:
                content_file.write(json.dumps(gallica_12148_f11))

            vlm = ViaLabelManager(tmpdir, None, None)
            scenes, warnings = vlm.load_all_labeled_files()

        # assert now the content of scenes
        self.assertEqual(1, len(scenes))
        self.assertEqual(0, len(warnings))
        f11 = scenes[0]
        self.assertEqual("60106", f11['mandragoreID'])
        self.assertEqual(
            "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11/398,195,2317,3945/full/0/native.jpg",
            f11['documentURL'])
        self.assertEqual("8470209-11", f11['imageID'])
        self.assertDictEqual(
            {
                'x': 398,
                'y': 195,
                'width': 2317,
                'height': 3945
            }, f11['size'])
        self.assertEqual(2, len(f11['descriptors']))
        self.assertEqual('armoiries', f11['descriptors'][0]['classID'])
        self.assertEqual('serpent', f11['descriptors'][1]['classID'])

    def test_record_scenes(self):
        with unittest.mock.patch('mdlg.persistence.db.PersistMandlagore',
                                 autospec=True) as MockDB:
            with unittest.mock.patch('mdlg.persistence.remoteHttp.Galactica',
                                     autospec=True) as MockGalactica:
                with MockDB() as db:
                    db.retrieve_image.return_value = None
                    gal = MockGalactica()
                    gal.collect_image_size.return_value = (1000, 2000)
                    vlm = ViaLabelManager(None, db, gal)

                    vlm.record_scenes(SCENES)

                    db.delete_mandragore_related.assert_called_once_with(
                        frozenset(['ID1', 'ID2']))
                    db.ensure_images.assert_called_once_with([
                        {
                            'imageID': 'doc-page1',
                            'documentURL':
                            'https://gallica.bnf.fr/iiif/ark:/12148/doc/page1/full/full/0/native.jpg',
                            'width': 1000,
                            'height': 2000
                        },
                        {
                            'imageID': 'doc-page2',
                            'documentURL':
                            'https://gallica.bnf.fr/iiif/ark:/12148/doc/page2/full/full/0/native.jpg',
                            'width': 1000,
                            'height': 2000
                        },
                    ])
