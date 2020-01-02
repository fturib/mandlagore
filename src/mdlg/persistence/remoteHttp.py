
import urllib.request
from mdlg.model.model import GalacticaURL
import json


class Galactica:

    @staticmethod
    def download_image(documentURL: str, filename: str):
        urllib.request.urlretrieve(documentURL, filename)

    @staticmethod
    def collect_image_size(documentURL: str) -> (int, int):
        url = GalacticaURL(documentURL)
        info_url = url.url_image_properties()

        with urllib.request.urlopen(info_url) as req:
            data = json.loads(req.read())

        # {"profile": "http://library.stanford.edu/iiif/image-api/1.1/compliance.html#level2",
        #  "width": 3239,
        #  "height": 4236,
        #  "@context": "http://library.stanford.edu/iiif/image-api/1.1/context.json",
        #  "@id": "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11"
        #  }

        return data["width"], data["height"]


class DRE:
    pass

