
import unittest
import tempfile
import persistence.db

class TestDB(unittest.TestCase):

    def test_creating_db(self):
        tmp = tempfile.NamedTemporaryFile(suffix='db', prefix='tmp-mdlg')
        with persistence.db.PersistMandlagore(tmp.name) as db:
            version = db.ensure_schema(rebuilt=True)
            self.assertIsNotNone(version)

    def test_fetching_image(self):
        IMAGE = {'imageID': 'name-page', 'documentURL': 'http://localhist:8080/whatever', 'width': 1000, 'height':2000}
        tmp = tempfile.NamedTemporaryFile(suffix='db', prefix='tmp-mdlg')
        with persistence.db.PersistMandlagore(tmp.name) as db:
            version = db.ensure_schema(rebuilt=True)            
            self.assertIsNotNone(version)
            db.ensure_images([IMAGE])
            data = db.retrieve_image(IMAGE['imageID'])
            self.assertTrue(len(data), 1)
