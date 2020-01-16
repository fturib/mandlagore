# images are physically saved:
# - in folder TOBEDEFINED, with a zoom version
# - the information is saved in DB (but not the image itself)
# -

# Images are saved locally in a flat folder (with all images) in jpg format
# Engines will have to read the real size of the image from the file (it may have been downloaded with a reduction parameter)

from mdlg.persistence.db import PersistMandlagore
from mdlg.model.model import GalacticaURL, SIZE_FULL
from mdlg.persistence.remoteHttp import GalacticaSession
import os
import click


class ImagesManager:
    def __init__(self, rootdir: str, db: PersistMandlagore, gal: GalacticaSession):
        super().__init__()
        self._rootdir = rootdir
        self._db = db
        self._gal = gal

    def ensure_content_images(self, filter, limit: int = None, dryrun: bool = False, faked=False):
        # filter: an iteratable on imagesIDs
        # ensure that each image of the DB has its content downloaded
        ids_and_urls, count = self._db.retrieve_images(('imageID', 'documentURL', 'width', 'height'), filter, limit)
        downloading = 0
        for id, url, w, h in ids_and_urls:
            downloading += 1
            gal = GalacticaURL.from_url(url)
            gal = gal.set_size(20)
            filename = os.path.join(self._rootdir, gal.as_filename())

            if w is None or h is None:
                click.echo(f"download {downloading}/{count} - retriveing and updating size for image {gal.as_filename()}")
                if not dryrun:
                    nw, nh = self._gal.collect_image_size(gal.as_url(), faked)
                    self._db.update_images([{'imageID': id, 'width': nw, 'height': nh}])

            if os.path.exists(filename):
                # TODO should verify if the file is the right one
                # TODO should check the size defined in the file
                pass
            else:
                title = f"Download {downloading}/{count} - {gal.as_url()}->{gal.as_filename()}"
                if dryrun:
                    click.echo(title)
                else:
                    self._gal.download_image(gal.as_url(), filename, title, faked)

    def ensure_documenting_sizes_of_images(self):
        # download missing sizes from the remote web services
        pass
