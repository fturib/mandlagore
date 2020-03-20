import unittest
from unittest.mock import patch, MagicMock
import mdlg.persistence.images as images
from mdlg.persistence.db import TABLES, PersistMandlagore
import os
import tempfile
from imageio import imread, imsave
import numpy as np
from dh_segment.utils.evaluation import Metrics
import zipfile as zipf
import tarfile as tar
from contextlib import contextmanager
import mdlg.services.ml_illumination_locations as ill
from collections import Counter
import functools
import test_db


@contextmanager
def build_zip_file(filenames) -> str:
    with tempfile.NamedTemporaryFile() as tf:
        z = zipf.ZipFile(tf, mode='w')
        for n in filenames:
            z.writestr(n, n)
        z.close()

        yield tf.name


@contextmanager
def build_tar_file(filenames) -> str:
    with tempfile.TemporaryDirectory() as tmpd:
        tarfn = os.path.join(tmpd, 'whatever-filename.tar')
        t = tar.TarFile(tarfn, mode='w')
        for n in filenames:
            fullfn = os.path.join(tmpd, n)
            with open(fullfn, 'w') as f:
                f.write(f"data of file {n}\n")
            t.add(fullfn, n)
        t.close()

        yield tarfn


class TestModelManager(unittest.TestCase):
    def test_new_install(self):
        TESTS = {
            'simple': (
                'my-model',
                ('model.bin', ),
            ),
            'several': ('amodel', ('model.whatever', 'data.txt', 'extrainfo.json')),
        }

        def install_and_check(files, mdir: str, name: str, url: str):
            mm = ill.ModelManager(mdir, name, url=url)
            mm.install()

            rfiles = os.listdir(mm.model_dir)
            self.assertEqual(set(rfiles), set(files))
            self.assertTrue(mm.is_installed())

            mm.clean()
            self.assertFalse(mm.is_installed())

        for k, v in TESTS.items():
            name, files = v
            with tempfile.TemporaryDirectory() as tmpd, build_zip_file(files) as z, build_tar_file(files) as t:
                model_dir = os.path.join(tmpd, 'model')
                install_and_check(files, model_dir, name, 'file://' + z)
                install_and_check(files, model_dir, name, 'file://' + t)


def prepare_fake_images(folder: str, names: tuple) -> tuple:
    for n in names:
        # create a basic source image of 100 x 100
        iz = images.ImageZones(n, 100, 100, ())
        img = iz.create_mask()
        fname = os.path.join(folder, ill.IMAGE_FILENAME.format(n))
        imsave(fname, img.astype(np.uint8))
        yield iz


def load_image(folder: str, name: str):
    fname = os.path.join(folder, ill.IMAGE_FILENAME.format(name))
    return imread(fname)


def fixed_zone_image_fetcher(folder: str, name: str, zones: tuple = ()) -> images.ImageZones:
    if os.path.exists(os.path.join(folder, ill.IMAGE_FILENAME.format(name))):
        return images.ImageZones(name, 100, 100, zones)
    return None


class TestImagesLabelsFolderManager(unittest.TestCase):
    def test_populate(self):
        TESTS = {
            'no-labels': ('image', True, ((5, 5, 20, 20), )),
            'with-labels': ('image', False, ((5, 5, 20, 20), )),
            'inv-image': ('inv-image', False, ((5, 5, 20, 20), ))
        }
        for k, (name, with_labels, prediction) in TESTS.items():
            with tempfile.TemporaryDirectory() as tmpd:
                # create a basic source image of 100 x 100
                iz = list(prepare_fake_images(tmpd, ('image', )))[0]
                fetcher = functools.partial(fixed_zone_image_fetcher, tmpd, zones=[])

                # create ILFolderManager and populate
                data_dir = os.path.join(tmpd, 'data')
                ilfm = ill.ImagesLabelsFolderManager(data_dir, with_labels, fetcher)
                self.assertTrue(ilfm.is_empty())
                consistent, total = ilfm.is_consistent()
                self.assertTrue(consistent)
                self.assertEqual(0, total)

                if name != 'image':
                    with self.assertRaises(ill.ExceptionFolderNotInitialized):
                        ilfm.populate_one(iz, data_dir)
                    continue

                ilfm.populate_one(iz, tmpd)
                self.assertFalse(ilfm.is_empty())

                # verify we have done all operations of populating
                self.assertTrue(os.path.exists(ilfm.image_path(iz)))
                self.assertEqual(with_labels, os.path.exists(ilfm.label_path(iz)))

                consistent, total = ilfm.is_consistent()
                self.assertTrue(consistent)
                self.assertEqual(1, total)

                imgl = ilfm.loadImage(iz)
                simg = load_image(tmpd, name)
                self.assertTrue(np.array_equal(simg, imgl))

                ilfm.generateView(iz, prediction)
                self.assertTrue(os.path.exists(ilfm.predict_path(iz)))

                izp = list(ilfm.pages())
                self.assertEqual(1, len(izp))
                self.assertEqual(izp[0], iz)

                ilfm.clean()
                self.assertTrue(ilfm.is_empty())
                consistent, total = ilfm.is_consistent()
                self.assertTrue(consistent)
                self.assertEqual(0, total)


class TestGlobalFunctions(unittest.TestCase):
    def test_generate_random_occurences(self):
        TESTS = {
            'one-name': {
                'name': 1.0
            },
            'two-names-pct': {
                'one': 0.2,
                'two': 0.8
            },
            'two-names-abs': {
                'one': 30,
                'two': 50
            },
            'several-names': {str(i): i
                              for i in range(10)},
        }

        def rate_to_pct(rate: dict) -> Counter:
            s = sum(rate.values())
            return Counter({n: int(v * 100 / s) for n, v in rate.items()})

        def substract(a: Counter, b: Counter) -> Counter:
            return Counter({k: a[k] - b[k] for k in set(a.keys()) | set(b.keys())})

        for k, rates in TESTS.items():
            data = Counter(n for _, n in zip(range(100), ill.generate_random_occurences(rates)))
            # transform rates into Counter on 100 total and substract to data
            # check that each value in data is less than 10%
            for n, r in substract(data, rate_to_pct(rates)).items():
                self.assertGreater(10, abs(r))

        pass


class TestNamesetDataManager(unittest.TestCase):
    def test_populate(self):
        TESTS = {'eval': (ill.EVAL_FOLDERS, 2), 'predict': (ill.PREDICT_FOLDERS, 10), 'training': (ill.TRAINING_FOLDERS, 20)}
        for k, (folders, nb_imgs) in TESTS.items():
            names = [f'img-{i}' for i in range(nb_imgs)]
            with tempfile.TemporaryDirectory() as tmpd:
                iiz = prepare_fake_images(tmpd, names)

                data_dir = os.path.join(tmpd, 'data')
                fetcher = functools.partial(fixed_zone_image_fetcher, tmpd, zones=[])
                ndm = ill.NamesetDataManager(k, data_dir, folders, fetcher)

                self.assertTrue(ndm.is_consistent()[0])

                ndm.populate(tmpd, iiz)

                # check the count of images
                c, counts = ndm.is_consistent()
                self.assertTrue(c)
                s = sum(map(lambda x: x[1], counts.values()))
                self.assertEqual(s, nb_imgs)

@contextmanager
def prepare_illumination_processor(data: dict, models: tuple = ()):
    with test_db.prepare_db(data) as db, tempfile.TemporaryDirectory() as tmpd:
        data_dir = os.path.join(tmpd, 'data')
        images_dir = os.path.join(tmpd, 'images')
        os.makedirs(images_dir)
        images = {d['imageID']: d for d in data['images']}
        izs = list(prepare_fake_images(images_dir, images.keys()))

        # create some models (fill the corresponding dir)
        models_dir = os.path.join('data', 'models')
        all_models = list(models) + list(ill.MODELS.keys())
        for name in models:
            with build_zip_file(('test-model', 'data')) as z:
                mm = ill.ModelManager(models_dir, name, url='file://' + z)
                mm.install()

        yield ill.MLIlluminationLocations(images_dir, data_dir, db), db, images


class TestMLIlluminationLocations(unittest.TestCase):

    def test_db_to_iz(self):
        TEST = {
            'all-images': ({
                'images': ({
                    'imageID': 'img-one',
                    'width': 10,
                    'height': 10
                }, )
            }, {
                'img-one': 0
            }),
            'image-one-scene': ({
                'images': ({
                    'imageID': 'img-one',
                    'width': 10,
                    'height': 10
                }, ),
                'scenes': ({
                    'imageID': 'img-one',
                    'x': 10,
                    'y': 10,
                    'width': 10,
                    'height': 10
                }, )
            }, {
                'img-one': 1
            }),
            'two-image-one-scene-each': ({
                'images': ({
                    'imageID': 'img-one',
                    'width': 10,
                    'height': 10
                }, {
                    'imageID': 'img-two',
                    'width': 20,
                    'height': 20
                }),
                'scenes': ({
                    'imageID': 'img-one',
                    'x': 100,
                    'y': 100,
                    'width': 100,
                    'height': 100
                }, {
                    'imageID': 'img-two',
                    'x': 20,
                    'y': 20,
                    'width': 20,
                    'height': 20
                }, {
                    'imageID': 'img-two',
                    'x': 3,
                    'y': 3,
                    'width': 30,
                    'height': 30
                })
            }, {
                'img-one': 1,
                'img-two': 2
            }),
        }

        for k, (data, zones) in TEST.items():
            with prepare_illumination_processor(data) as (ip, db, imgs):
                # iterate over all images of the DB, verify ImageZone is correct, and we can fetch the image
                imgiter, tot = db.retrieve_images(TABLES['images'].all_fields + list(TABLES['scenes'].qualified(TABLES['scenes'].all_fields)),
                                                  [('scenes', None, None)], all=True, with_field_names=True)
                for iz in ip.db_to_iz(imgiter):
                    # verify iz is a real image
                    self.assertTrue(iz.name in imgs.keys())
                    img = imgs.pop(iz.name)
                    self.assertEqual((iz.w, iz.h), (img['width'], img['height']))
                    self.assertEqual(len(iz.zones), zones[iz.name])
                    izf = ip.iz_fetcher(iz.name)
                    # iz fetcher is supposed to retrieve the original iz from DB
                    self.assertEqual(izf, iz)
                # verify we ran over all images of the DB (filter is empty)
                self.assertEqual(len(imgs), 0)

    @patch('mdlg.services.ml_illumination_locations.MLIlluminationLocations.train')
    @patch('mdlg.services.ml_illumination_locations.MLIlluminationLocations.predict')
    def test_execute(self, mock_predict, mock_train):
        DATA = {
            'images': ({
                'imageID': 'img-one',
                'width': 10,
                'height': 10
            }, {
                'imageID': 'img-two',
                'width': 20,
                'height': 20
            }),
            'scenes': ({
                'imageID': 'img-one',
                'x': 100,
                'y': 100,
                'width': 100,
                'height': 100
            }, {
                'imageID': 'img-two',
                'x': 20,
                'y': 20,
                'width': 20,
                'height': 20
            }, {
                'imageID': 'img-two',
                'x': 3,
                'y': 3,
                'width': 30,
                'height': 30
            })
        }
        TEST = {'predict': ('predict', '', 'predict-model'), 'train': ('train', 'resnet50', 'trained-model')}

        def check_model(model: ill.ModelManager, modelName: str, installed=True):
            self.assertIsNotNone(model)
            self.assertEqual(modelName, model.name)
            self.assertEqual(installed, model.is_installed())

        def check_imgfolder(folder: ill.ImagesLabelsFolderManager, withlabels: bool, nb_images: int):
            self.assertIsNotNone(folder)
            self.assertEqual(withlabels, folder.with_labels)
            c, tot = folder.is_consistent()
            self.assertTrue(c)
            self.assertEqual(nb_images, tot)

        def check_dataset(dataset: ill.NamesetDataManager, name: str, folders: dict, nb_images: int):
            self.assertIsNotNone(dataset)
            self.assertEqual(name, dataset.nameset)
            c, f = dataset.is_consistent()
            self.assertTrue(c)
            self.assertEqual(len(folders), len(f))
            for n, (wl, _) in folders.items():
                self.assertEqual(dataset.folders[n].with_labels, wl)
                self.assertTrue(f[n][0])
            self.assertEqual(nb_images, sum(map(lambda x: x[1], f.values())))

        for k, params in TEST.items():
            with prepare_illumination_processor(DATA, ('predict-model', 'trained-model')) as (ip, db, imgs):
                ip.execute(params[0], params[1], params[2], 'example')
                # assert env is setup properly
                # assert the right function has been called with the right parameters
                if params[0] == 'predict':
                    model, predictfolder = mock_predict.call_args[0]
                    check_model(model, params[2], installed=True)
                    check_imgfolder(predictfolder, False, len(DATA['images']))

                elif params[0] == 'train':
                    premodel, model, dataset = mock_train.call_args[0]
                    check_model(premodel, params[1], installed=True)
                    check_model(model, params[2], installed=False)
                    check_dataset(dataset, 'example', ill.TRAINING_FOLDERS, len(DATA['images']))

    def test_predict(self):
        pass

    def test_train(self):
        pass
