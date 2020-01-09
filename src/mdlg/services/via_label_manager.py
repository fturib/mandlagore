import json
import os
from mdlg.model.model import GalacticaURL, zone_in_zone_as_pct, ZONE_FULL
import tempfile
import click
from mdlg.persistence.remoteHttp import CannotRetriveInformation

# JSON_DATA_PATH = "/Users/francois/Documents/Mandragore/DetourageImages"


class InvalidFilenameError(Exception):
    pass


class ViaLabelManager:

    # Labels are delivered in JSON files encoded (UTF-8) :
    # Each file is a dict (documentURL, dict( - description - )
    # {"https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11/398,195,2317,3945/full/0/native.jpg-1":
    #      {"filename":"https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11/398,195,2317,3945/full/0/native.jpg",
    #       "size":-1,
    #       "regions":[
    #           {"shape_attributes":
    #                {"name":"rect",
    #                 "x":449,
    #                 "y":1610,
    #                 "width":1363,
    #                 "height":1257},
    #            "region_attributes":
    #                {"Descripteur":"armoiries",
    #                 "Type":"objet"}
    #           },
    #           {"shape_attributes":{
    #               "name":"rect",
    #               "x":656,
    #               "y":122,
    #               "width":875,
    #               "height":568},
    #             "region_attributes":{
    #                 "Descripteur":"serpent",
    #                 "Type":"objet"}
    #           },
    #           ...
    #       ],
    #       "file_attributes":{
    #           "MandragoreId":"60106"}
    #       }
    #       ...
    #  }

    def __init__(self, rootdir, db, galactica):
        self.rootdir = rootdir
        self.db = db
        self.galactica = galactica
        pass

    def list_labeled_files(self) -> []:
        files = []
        for r, d, f in os.walk(self.rootdir):
            for file in f:
                if '.json' in file:
                    files.append(os.path.join(r, file))
        return files

    def load_all_labeled_files(self) -> ([], []):
        scenes = []
        warnings = []
        for f in self.list_labeled_files():
            sc, wa = self.load_one_labeled_file(f)
            scenes.extend(sc)
            warnings.extend(wa)

        return scenes, warnings

    def load_one_labeled_file(self, filepath) -> ([], []):
        # We suppose the DB is ready and cleaned

        with open(filepath, "r") as fp:
            data = json.load(fp)

        scenes = []
        warnings = []
        for v in data.values():
            try:
                scene = self._describe_one_scene(v)
                scenes.append(scene)
            except InvalidFilenameError as e:
                warnings.append("file %s - one scene cannot be prepared for import. Reason : %s" % (filepath, str(e)))

        return scenes, warnings

    @staticmethod
    def _describe_one_scene(via_data) -> dict:
        # decode the URL and get information from it
        url = GalacticaURL.from_url(via_data["filename"])

        # check we are on the Gallactica format

        if not url.is_valid():
            raise InvalidFilenameError('the url : {0} is not a valid galactica url'.format(via_data["filename"]))

        # need to check if one of the params is "pct:xx"
        # -> provide the zoom on the image and therefore the right locations
        zoom = 100

        image_id = "%s-%s" % (url.document_id(), url.page_number())
        document_url = via_data['filename']
        mandragore_id = via_data['file_attributes']['MandragoreId']
        descriptors = []

        size_image = url.zone()
        for region in via_data['regions']:
            class_id = region['region_attributes']['Descripteur']
            size_px = region['shape_attributes']
            descriptors.append({'classID': class_id, 'location': size_px})

        return {'mandragoreID': mandragore_id, 'documentURL': document_url, 'imageID': image_id, 'size': size_image, 'descriptors': descriptors}

    def record_scenes(self, scenes, title='prepare scenes') -> str:
        # ensure to delete data tied to the corresponding 'mandragoreID'
        # then add
        #   - images's records
        #   - scene's records
        #   - descriptors's records

        # build all lists of information needed to create the data related to the scenes

        mandragore_ids = set()
        images_fields = []
        scene_fields = []
        descriptor_fields = []
        with click.progressbar(scenes, label=title) as bar:
            for sc in bar:
                mandragore_ids.add(sc['mandragoreID'])
                image = self.db.retrieve_image(sc['imageID'])
                gal = GalacticaURL.from_url(sc['documentURL']).set_zone(ZONE_FULL)
                # TODO - WARNING - we may have a side effect on location of scenes and descriptors if the initial image has been resized in VIA (eg pct:50)
                if image is None or image['width'] is None or image['height'] is None:
                    # need to retrieve the size of the image
                    w, h = None, None
                    try:
                        w, h = self.galactica.collect_image_size(gal.as_url())
                    except CannotRetriveInformation as cri:
                        # TODO - Manage exception
                        pass
                    images_fields.append({'imageID': sc['imageID'], 'documentURL': gal.as_url(), 'width': w, 'height': h})
                else:
                    w, h = image['width'], image['height']

                scene_info = {'mandragoreID': sc['mandragoreID'], 'imageID': sc['imageID']}
                scene_info.update(sc['size'])
                scene_fields.append(scene_info)

                for d in sc['descriptors']:
                    desc_info = {'mandragoreID': sc['mandragoreID'], 'classID': d['classID']}
                    desc_info.update(d['location'])
                    descriptor_fields.append(desc_info)
        try:
            self.db.delete_mandragore_related(mandragore_ids)
            self.db.ensure_images(images_fields)
            self.db.add_scenes(scene_fields)
            self.db.add_descriptors(descriptor_fields)
            return "%d scenes imported in DB." % len(scenes)
        except Exception as e:
            return "Was not able to import the %d scenes in DB. Reason : %s" % (len(scenes), str(e))

    def import_labels(self) -> ():
        report = []
        files = self.list_labeled_files()
        if len(files) > 0:
            for f in files:
                scenes, warnings = self.load_one_labeled_file(f)
                rep = self.record_scenes(scenes, f)
                report.append((f, warnings, rep))
        else:
            report.append(("--NO FILE--", [], "No .json files found in %s" % self.rootdir))
        return report
