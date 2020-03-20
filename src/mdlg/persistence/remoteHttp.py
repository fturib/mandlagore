import requests
from mdlg.model.model import GalacticaURL
import json
from requests import RequestException, Session, get
from urllib.request import url2pathname
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
        if len(rd) <= 0:
            break


# code provided here : https://stackoverflow.com/questions/10123929/fetch-a-file-from-a-local-url-with-python-requests
class LocalFileAdapter(requests.adapters.BaseAdapter):
    """Protocol Adapter to allow Requests to GET file:// URLs

    @todo: Properly handle non-empty hostname portions.
    """
    @staticmethod
    def _chkpath(method, path):
        """Return an HTTP status for the given filesystem path."""
        if method.lower() in ('put', 'delete'):
            return 501, "Not Implemented"  # TODO
        elif method.lower() not in ('get', 'head'):
            return 405, "Method Not Allowed"
        elif os.path.isdir(path):
            return 400, "Path Not A File"
        elif not os.path.isfile(path):
            return 404, "File Not Found"
        elif not os.access(path, os.R_OK):
            return 403, "Access Denied"
        else:
            return 200, "OK"

    def send(self, req, **kwargs):  # pylint: disable=unused-argument
        """Return the file specified by the given request

        @type req: C{PreparedRequest}
        @todo: Should I bother filling `response.headers` and processing
               If-Modified-Since and friends using `os.stat`?
        """
        path = os.path.normcase(os.path.normpath(url2pathname(req.path_url)))
        response = requests.Response()

        response.status_code, response.reason = self._chkpath(req.method, path)
        if response.status_code == 200 and req.method.lower() != 'head':
            try:
                response.raw = open(path, 'rb')
            except (OSError, IOError) as err:
                response.status_code = 500
                response.reason = str(err)

        if isinstance(req.url, bytes):
            response.url = req.url.decode('utf-8')
        else:
            response.url = req.url

        response.request = req
        response.connection = self

        return response

    def close(self):
        pass


class FakeDownloadResponse(object):
    def __init__(self, content: str = "ABCDEFGHIJKLMNOPQR", status=200):
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


def download_binary_file(session: requests.Session, url: str, filename: str, titlebar: str = None, dryrun: bool = False):

    if dryrun:
        r = FakeDownloadResponse()
    else:
        if session is None:
            session = requests.session()
        session.mount('file://', LocalFileAdapter())
        r = session.get(url)

    try:
        r.raise_for_status()
        total_size = int(r.headers['content-length']) if 'content-length' in r.headers else -1
        with progressbar(r.iter_content(1024), length=total_size if total_size >= 0 else None, label=url if titlebar is None else titlebar) as bar:
            with open(filename, 'wb') as fd:
                for chunk in bar:
                    bar.update(fd.write(chunk))

    except RequestException as re:
        clean_file(filename)
        raise CannotRetriveInformation("getting url : %s - return status code %d (exception raised is : %s)" % (url, r.status_code, str(re)))
    except IOError as e:
        clean_file(filename)
        raise CannotRetriveInformation("saving url: %s in file %s - (exception raised is : %s)" % (url, filename, str(e)))


def download_json(session: requests.Session, url: str) -> object:
    try:
        r = session.get(url)
        r.raise_for_status()
    except RequestException as re:
        raise CannotRetriveInformation("getting url : %s - return status code %d (exception raised is : %s)" % (url, r.status_code, str(re)))

    return r.json()


class GalacticaSession(object):
    def __init__(self):
        super().__init__()
        self._session = None

    def __enter__(self):
        self._session = requests.Session()
        return self

    def __exit__(self, *exc):
        self._session = None

    def download_image(self, documentURL: str, filename: str, titlebar: str = None, dryrun: bool = False):
        download_binary_file(self._session, documentURL, filename, titlebar, dryrun)

    def collect_image_size(self, documentURL: str, dryrun: bool = False) -> (int, int):
        if dryrun:
            return 10, 20
        else:
            url = GalacticaURL.from_url(documentURL).url_image_properties().as_url()
            data = download_json(self._session, url)
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
