
import json
import os
import model.model
import tempfile

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

    def load_all_labeled_files(self) -> []:
        files =[]
        for r, d, f in os.walk(self.rootdir):
            for file in f:
                if '.json' in file:
                    files.append(os.path.join(r, file))

        scenes = []
        for f in files:
            scenes.extend(self.load_one_labeled_file(f))

        return scenes

    def load_one_labeled_file(self, filepath) -> []:
        # We suppose the DB is ready and cleaned

        with open(filepath, "r") as fp:
            data = json.load(fp)

        scenes = []
        for v in data.values():
            try:
                scene = self._describe_one_scene(v)
                scenes.append(scene)
            except InvalidFilenameError:
                pass # just ignore for now - as we want others to be added

        return scenes

    @staticmethod
    def _describe_one_scene(via_data) -> dict:
        # decode the URL and get information from it
        url = model.model.GalacticaURL(via_data["filename"])

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

        for region in via_data['regions']:
            class_id = region['region_attributes']['Descripteur']
            size_px = region['shape_attributes']
            size_pct = model.model.zone_in_zone_as_pct(url.size_px(), size_px)

            descriptors.append({'classID':class_id, 'location':size_pct})

        return {'mandragoreID' : mandragore_id, 'documentURL':document_url, 'imageID':image_id,
                'size_px': url.size_px(), 'descriptors':descriptors}

    def record_scenes(self, scenes):
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
        for sc in scenes:
            mandragore_ids.add(sc['mandragoreID'])
            image = self.db.retrieve_image(sc['imageID'])
            if image is None:
                # need to retrieve the size of the image
                w, h = self.galactica.collect_image_size(sc['documentURL'])
                images_fields.append({'imageID': sc['imageID'], 'documentURL': sc['documentURL'], 'width': w, 'height': h})
            else:
                w, h = image['width'], image['height']

            scene_info = {'mandragoreID': sc['mandragoreID'], 'imageID': sc['imageID']}
            scene_info.update(model.model.zone_in_zone_as_pct({'x': 1, 'y': 1, 'width': w, 'height': h}, sc['size_px']))
            scene_fields.append(scene_info)

            for d in sc['descriptors']:
                desc_info = {'mandragoreID': sc['mandragoreID'], 'classID': d['classID']}
                desc_info.update(d['location'])
                descriptor_fields.append(desc_info)

        self.db.delete_mandragore_related(mandragore_ids)
        self.db.ensure_images(images_fields)






