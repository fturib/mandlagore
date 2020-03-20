from mdlg.persistence.db import PersistMandlagore, TABLES
from mdlg.persistence.images import ImageZones, get_image_shape_without_loading
from mdlg.model.model import ZONE_KEYS
from mdlg.persistence.remoteHttp import download_binary_file
from mdlg.persistence.files import extract

import os
import shutil
from random import seed, random
from typing import Iterable
from itertools import groupby
from tempfile import TemporaryDirectory

import numpy as np
import tensorflow as tf
import tensorflow_estimator as tfe
from imageio import imread, imsave
from tqdm import tqdm, trange

from dh_segment.io import input
from dh_segment.inference import LoadedModel
from dh_segment.utils.params_config import TrainingParams, ModelParams, PredictionType
from dh_segment.estimator_fn import model_fn
from dh_segment.utils.evaluation import Metrics

MODELS = {
    'resnet50': (True, 'http://download.tensorflow.org/models/resnet_v1_50_2016_08_28.tar.gz', 'resnet_v1_50.tar.gz'),
    'vgg-16': (True, 'http://download.tensorflow.org/models/vgg_16_2016_08_28.tar.gz', 'vgg_16.tar.gz'),
    'resnet-border': (False, 'https://github.com/dhlab-epfl/dhSegment/releases/download/v0.2/model.zip', 'model.zip')
}


class ModelManager:
    """ Manage model's persistence from a root folder.
    """
    def __init__(self, models_dir, modelName, url=None):
        self.model_dir = os.path.join(models_dir, modelName)
        self.export_dir = os.path.join(self.model_dir, 'export')
        os.makedirs(self.export_dir, exist_ok=True)
        self.name = modelName
        if modelName in MODELS:
            self.is_premodel, self.url, self.filename = MODELS[modelName]
        else:
            self.is_premodel, self.url, self.filename = False, None, None
        if url is not None:
            self.url = url

    def is_installed(self):
        return os.path.exists(self.model_dir) and len(os.listdir(self.model_dir)) > 0

    def clean(self):
        shutil.rmtree(self.model_dir)
        os.makedirs(self.model_dir, exist_ok=True)

    def install(self):
        # first download the file, then extract (tar of zip)
        os.makedirs(self.model_dir, exist_ok=True)
        if self.url is not None:
            filename = self.filename if self.filename is not None else self.name
            with TemporaryDirectory() as tmpdir:
                datafile = os.path.join(tmpdir, filename)
                download_binary_file(None, self.url, datafile)
                extract(datafile, self.model_dir)
                self.filename = filename


IMAGE_FILENAME = "{}.jpg"
LABEL_FILENAME = "{}.png"
OVERVIEW_FILENAME = "{}_boxes.jpg"


class ExceptionFolderNotInitialized(Exception):
    pass


class ImagesLabelsFolderManager:
    """ Manage the persistence on file of Images, Labels and prediction output
        It uses help of a fetcher from DB for information in DB
    """
    def __init__(self, data_dir, with_labels: bool, iz_fetcher):
        super().__init__()
        self.data_dir = data_dir
        self.with_labels = with_labels
        self.iz_fetcher = iz_fetcher
        self.images_dir = os.path.join(self.data_dir, 'images')
        self.labels_dir = os.path.join(self.data_dir, 'labels')
        self.predict_dir = os.path.join(self.data_dir, 'predict')
        self.clean(False)

    def is_consistent(self) -> (bool, int):
        # verify you have a label for each image
        tot = 0
        self.check_initialized()

        for f in os.listdir(self.images_dir):
            tot += 1
            if self.with_labels:
                # check if corresponding label already exist
                labelfile = os.path.join(self.labels_dir, LABEL_FILENAME.format(f[:-4]))
                if not os.path.exists(labelfile):
                    return False, -1

        return True, tot

    def is_empty(self) -> bool:
        if not os.path.exists(self.data_dir):
            return True

        consistent, total = self.is_consistent()
        return consistent and total == 0

    def check_initialized(self):
        if not os.path.exists(self.data_dir):
            raise ExceptionFolderNotInitialized(f"folder {self.data_dir} is missing")

        if not os.path.exists(self.images_dir):
            raise ExceptionFolderNotInitialized(f"folder {self.images_dir} is missing")

        if self.with_labels and not os.path.exists(self.labels_dir):
            raise ExceptionFolderNotInitialized(f"folder {self.labels_dir} is missing")

        if not os.path.exists(self.predict_dir):
            raise ExceptionFolderNotInitialized(f"folder {self.predict_dir} is missing")

    def clean(self, force_delete=True):
        if os.path.exists(self.data_dir) and force_delete:
            shutil.rmtree(self.data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        if self.with_labels:
            os.makedirs(self.labels_dir, exist_ok=True)
        os.makedirs(self.predict_dir, exist_ok=True)

    def image_path(self, iz: ImageZones):
        return os.path.join(self.images_dir, IMAGE_FILENAME.format(iz.name))

    def label_path(self, iz: ImageZones):
        return os.path.join(self.labels_dir, LABEL_FILENAME.format(iz.name))

    def predict_path(self, iz: ImageZones):
        return os.path.join(self.predict_dir, OVERVIEW_FILENAME.format(iz.name))

    def loadImage(self, iz: ImageZones) -> np.array:
        self.check_initialized()
        return imread(self.image_path(iz))

    def generateLabel(self, iz: ImageZones):
        self.check_initialized()
        img = iz.draw_zones(iz.create_mask(), iz.zones, False)
        imsave(self.label_path(iz), img.astype(np.uint8))

    def generateView(self, iz: ImageZones, predicted_zones):
        self.check_initialized()
        img = self.loadImage(iz)
        img = iz.draw_zones(img, iz.zones, True)
        img = iz.draw_zones(img, predicted_zones, True)
        imsave(self.predict_path(iz), img.astype(np.uint8))

    def populate_one(self, iz, sourceFolder):
        # copy the img content to the right folder
        # apply scale to the zones
        # and create a ImageZones to manage labels, content and image result

        destfile = self.image_path(iz)
        srcfile = os.path.join(sourceFolder, os.path.basename(destfile))
        if not os.path.exists(srcfile):
            raise ExceptionFolderNotInitialized(f"Cannot retrieve source image : {srcfile}")

        shutil.copyfile(srcfile, destfile)

        fw, fh = get_image_shape_without_loading(destfile)
        scaled_iz = iz.rescale(fw, fh)
        if self.with_labels:
            self.generateLabel(scaled_iz)

    def populate(self, images_dir: str, images_iter):
        # Class file
        for iz in images_iter:
            self.populate_one(iz, images_dir)

    def pages(self) -> Iterable:
        # iterate over all images
        for f in os.listdir(self.images_dir):
            name = f[:-4]
            unscaled_iz = self.iz_fetcher(name)
            w, h = get_image_shape_without_loading(os.path.join(self.images_dir, f))
            yield unscaled_iz.rescale(w, h)


# { name-of-folder: (with-labels, rate-at-image-population)}
TRAIN_NAME, TEST_NAME, EVAL_NAME, PREDICT_NAME = 'train', 'test', 'eval', 'predict'
TRAINING_FOLDERS = {TRAIN_NAME: (True, 0.6), TEST_NAME: (True, 0.2), EVAL_NAME: (True, 0.2)}
EVAL_FOLDERS = {EVAL_NAME: (True, 1.0)}
PREDICT_FOLDERS = {PREDICT_NAME: (False, 1.0)}


def generate_random_occurences(occurences: dict()):
    # splitrate is in the form {name : %occurence}
    # it returns an iterator if names that happen at the expected occurence
    rg = {}
    mx = 0.0
    for n, v in occurences.items():
        mn = mx
        mx += v
        rg[n] = (mn, mx)

    seed()

    def gen():
        while True:
            r = random() * mx
            for n, (l, h) in rg.items():  # load it to all the deques
                if r >= l and r < h:
                    yield n
                    break

    return gen()


class NamesetDataManager:
    def __init__(self, nameset: str, data_dir: str, folders: dict, iz_fetcher):
        self.filter = filter
        self.nameset = nameset
        self.set_dir = os.path.join(data_dir, self.nameset)
        self.folders = {n: ImagesLabelsFolderManager(os.path.join(self.set_dir, n), l, iz_fetcher) for n, (l, _) in folders.items()}
        self.split = {n: d for n, (_, d) in folders.items()}
        self.clean(False)

    def is_consistent(self) -> (bool, dict):
        counts = dict(map(lambda x: (x[0], x[1].is_consistent()), self.folders.items()))
        return all(map(lambda x: x[0], counts.values())), counts

    def clean(self, force=True):
        # just remove the whole subtree
        if force and os.path.exists(self.set_dir):
            shutil.rmtree(self.set_dir)
        os.makedirs(self.set_dir, exist_ok=True)
        for f in self.folders.values():
            f.clean(force)

    def populate(self, images_dir: str, images_iter):
        # Apply a random distribution according to split rates. We do not need to shuffle input at this point
        for n, iz in zip(generate_random_occurences(self.split), images_iter):
            self.folders[n].populate_one(iz, images_dir)

        # save the classes.txt in the nameset dir
        # classes = np.stack([(0, 0, 0), (0, 255, 0)])
        # np.savetxt(os.path.join(self._data_dir, 'classes.txt'), classes, fmt='%d')


class MLIlluminationLocations(object):
    def __init__(self, src_images: str, data_dir: str, db: PersistMandlagore):
        self.data_dir = data_dir
        self.images_dir = src_images
        self.db = db

    def db_to_iz(self, imagesDBIter: Iterable):

        for k, g in groupby(imagesDBIter, key=lambda x: x['imageID']):
            item = None
            zones = []
            refw, refh = -1, -1
            for data in g:
                if item is None:
                    refw = data['width']
                    refh = data['height']

                # if there is scenes information add to the working item location
                if data['scenes.imageID'] is not None:
                    zones.append([data[f] for f in TABLES['scenes'].qualified(ZONE_KEYS)])

            yield ImageZones(k, refw, refh, zones)

    def iz_fetcher(self, nameImage: str) -> ImageZones:
        zones = ([data[f] for f in ZONE_KEYS] for data in self.db.retrieve_scenes_of_image(nameImage))
        img = self.db.retrieve_image(nameImage)
        return ImageZones(img['imageID'], img['width'], img['height'], zones)

    def predict(self, model: ModelManager, folder: ImagesLabelsFolderManager):
        # run the dhSegment prediction on a set of images
        # return the predictions
        # load image, run the predict, return the result in some way that we can compare;
        #   - maybe create an image with the boxes found by predict
        #   - compute the error with provided xywh if we have some from DB
        # SAVE the prediction somewhere in DB

        # If the model has been trained load the model, otherwise use the given model

        with tf.Session():  # Start a tensorflow session
            # Load the model
            m = LoadedModel(model.model_dir, predict_mode='filename')
            ev = Metrics()
            for iz in tqdm(folder.pages(), desc='Processed files'):
                # For each image, predict each pixel's label
                boxes = m.predict(folder.find_boxes(iz))
                predicted_zones = iz.predict(boxes)
                folder.generateView(iz, predicted_zones)
                ev += iz.eval(predicted_zones)
                # TODO - save the prediction in DB or in file for later usage

            ev.compute_miou()
            ev.compute_accuracy()
            ev.compute_prf()

        return {'precision': ev.precision, 'recall': ev.recall, 'f_measure': ev.f_measure, 'mIOU': ev.mIOU}

    def train(self, premodel: ModelManager, model: ModelManager, data: NamesetDataManager):
        # models and datasets are ready
        # we need a training config
        # we need to define how the result is returned

        # TODO - save the config in DB with training informations

        pretrained_model_name = 'resnet50'
        tp = TrainingParams()
        mp = ModelParams(pretrained_model_name=pretrained_model_name).to_dict()
        mp['n_classes'] = 1
        gpu = ''
        hyperparams = {
            'pretrained_model_name': pretrained_model_name,
            'prediction_type': PredictionType.REGRESSION,
            'model_params': mp,
            'training_params': tp,
            'gpu': gpu
        }

        sc = tf.ConfigProto()
        sc.gpu_options.visible_device_list = str(gpu)
        sc.gpu_options.per_process_gpu_memory_fraction = 0.9
        estimator_config = tfe.estimator.RunConfig().replace(session_config=sc, save_summary_steps=10, keep_checkpoint_max=1)
        estimator = tfe.estimator.Estimator(model_fn, model_dir=model.model_dir, params=hyperparams, config=estimator_config)

        do_eval = TEST_NAME in data.folders
        train_input, train_labels_input = data.folders[TRAIN_NAME].images_dir, data.folders[TRAIN_NAME].labels_dir
        if do_eval:
            eval_input, eval_labels_input = data.folders[TEST_NAME].images_dir, data.folders[TEST_NAME].labels_dir

        # Configure exporter
        serving_input_fn = input.serving_input_filename(tp.input_resized_size)
        if not do_eval:
            exporter = tfe.estimator.BestExporter(serving_input_receiver_fn=serving_input_fn, exports_to_keep=2)
        else:
            exporter = tfe.estimator.LatestExporter(name='SimpleExporter', serving_input_receiver_fn=serving_input_fn, exports_to_keep=5)

        for i in trange(0, tp.n_epochs, tp.evaluate_every_epoch, desc='Evaluated epochs'):
            estimator.train(
                input.input_fn(train_input,
                               input_label_dir=train_labels_input,
                               num_epochs=tp.evaluate_every_epoch,
                               batch_size=tp.batch_size,
                               data_augmentation=tp.data_augmentation,
                               make_patches=tp.make_patches,
                               image_summaries=True,
                               params=hyperparams,
                               num_threads=32))

            if do_eval:
                eval_result = estimator.evaluate(
                    input.input_fn(eval_input,
                                   input_label_dir=eval_labels_input,
                                   batch_size=1,
                                   data_augmentation=False,
                                   make_patches=False,
                                   image_summaries=False,
                                   params=hyperparams,
                                   num_threads=32))
            else:
                eval_result = None

            exporter.export(estimator, model.export_dir(), checkpoint_path=None, eval_result=eval_result, is_the_final_export=False)

    def execute(self, action: str, premodel_name: str, model_name: str, nameset: str, filter: tuple = (), limit: int = None) -> ():
        # entry point for dhSegment operations
        # :param action - one of the following 'predict', 'train', 'eval', 'clean'
        # :param pre_model - for training, which prebuilt model to use (one of the models typed 'pre-trained') - useless for other actions
        # :param model - for training, which model is generated, for predict or eval, which model to use
        # :param nameset - give a name to the set for training, prediction of evaluation. Used to separate and reuse the image/label sets
        # :param filter - a way to select the images for the operation. if data for nameset is already existing, it will be reused,
        #                 unless nameset is named 'volatile'
        # :param limit - max number of image to process during this action

        def prepare_image_set(folders):
            imgset = NamesetDataManager(nameset, namesets_dir, folders, self.iz_fetcher)
            locfilter = list(filter) + [('scenes', None, None)]
            fieldNames = TABLES['images'].all_fields + list(TABLES['scenes'].qualified(TABLES['scenes'].all_fields))
            images, tot = self.db.retrieve_images(fieldNames, locfilter, all=True, with_field_names=True)

            # TODO: we may want to keep existing set if seems consistent with number of images
            # need to know if we clean and populate with filter,
            # or keep existing data - it has to be consistent
            imgset.clean()
            imgset.populate(self.images_dir, self.db_to_iz(images))
            return imgset

        def prepare_model(model_name, check_mode, install_mode):
            model = ModelManager(models_dir, model_name)
            if check_mode == 'premodel':
                if not model.is_premodel:
                    raise Exception(f"The model : {model_name} is not a pre-trained model, as expected for the operation")
            elif check_mode == 'model':
                if model.is_premodel:
                    raise Exception(f"The model : {model_name} is a pre-trained model, and we expect to generate this model in the training operation")

            if install_mode == 'force_clean':
                model.clean()
            elif install_mode in ('force_install', 'install'):
                if install_mode == 'force_install':
                    model.clean()
                if not model.is_installed():
                    model.install()
                    if not model.is_installed():
                        raise Exception(f"The model : {model_name} is not a downloadable model. It has to be generated before usage - see training maybe")

            return model

        models_dir = os.path.join(self.data_dir, 'models')
        namesets_dir = os.path.join(self.data_dir, 'datasets')
        if action == 'train':
            premodel = prepare_model(premodel_name, 'premodel', 'install')
            model = prepare_model(model_name, 'model', 'force_clean')
            imgset = prepare_image_set(TRAINING_FOLDERS)
            self.train(premodel, model, imgset)
            # now we would like to evaluate the result against labels saved in EVAL_NAME folder
            self.predict(model, imgset.folders[EVAL_NAME])

        elif action == 'eval':
            # TODO - we may not need a model here ...
            pass

        elif action == 'predict':
            model = prepare_model(model_name, 'model', 'install')
            imgset = prepare_image_set(PREDICT_FOLDERS)
            self.predict(model, imgset.folders[PREDICT_NAME])
        else:
            raise Exception(f"The action : {action} is unknown in dhsegment context")

        # should return some report
        return ()
