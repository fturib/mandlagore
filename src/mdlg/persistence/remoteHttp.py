import requests
from mdlg.model.model import GalacticaURL
import json
from requests import RequestException
from click import progressbar
import os
import io


class CannotRetriveInformation(Exception):
    pass

def iter_slices(string, slice_length):
    """Iterate over slices of a string."""
    pos = 0
    arr = io.BytesIO(string.encode('utf-8'))
    if slice_length is None or slice_length <= 0:
        slice_length = 1024
    while True:
        rd = arr.read(slice_length)
        yield rd
        if len(rd) <=0:
            break

class FakeDownloadResponse(object):

    def __init__(self, content:str="ABCDEFGHIJKLMNOPQR", status = 200):
        super().__init__()
        self._content = content
        self._status = 200
        self.headers = {'content-length': len(self._content)}

    def raise_for_status(self):
        if self._status != 200:
            raise RequestException(f"status returned is {self._status}")

    def iter_content(self, chunk_size=1):
            return iter_slices(self._content, chunk_size)

def clean_file(filename: str):
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except Exception:
            pass


def download_binary_file(url:str, filename:str, titlebar:str=None, dryrun:bool=False):
    try:
        r = FakeDownloadResponse() if dryrun else requests.get(url, stream=True)
        r.raise_for_status()
        total_size = int(r.headers['content-length'])
        with progressbar(r.iter_content(1024), length=total_size, label=url if titlebar is None else titlebar) as bar:
            with open(filename, 'wb') as fd:
                for chunk in bar:
                    bar.update(fd.write(chunk))

    except RequestException as re:
        clean_file(filename)
        raise CannotRetriveInformation("getting url : %s - return status code %d (exception raised is : %s)" % (url, r.status_code, str(re)))
    except IOError as e:
        clean_file(filename)
        raise CannotRetriveInformation("saving url: %s in file %s - (exception raised is : %s)" % (url, filename, str(e)))


def download_json(url: str) -> object:
    try:
        r = requests.get(url)
        r.raise_for_status()
    except RequestException as re:
        raise CannotRetriveInformation("getting url : %s - return status code %d (exception raised is : %s)" % (url, r.status_code, str(re)))

    return r.json()


class Galactica:
    @staticmethod
    def download_image(documentURL: str, filename: str, titlebar:str=None, dryrun:bool=False):
        download_binary_file(documentURL, filename, titlebar, dryrun)

    @staticmethod
    def collect_image_size(documentURL: str, dryrun:bool=False) -> (int, int):
        if dryrun:
            return 10, 20
        else:
            url = GalacticaURL.from_url(documentURL).url_image_properties().as_url()
            data = download_json(url)
            if "width" not in data or "height" not in data:
                raise CannotRetriveInformation("getting url : %s - request return is correct, but json data does not containe wiht/height : JSON = %s" %
                                            (url, json.dumps(data)))
            return data["width"], data["height"]

        # {"profile": "http://library.stanford.edu/iiif/image-api/1.1/compliance.html#level2",
        #  "width": 3239,
        #  "height": 4236,
        #  "@context": "http://library.stanford.edu/iiif/image-api/1.1/context.json",
        #  "@id": "https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11"
        #  }


class DRE:
    pass

