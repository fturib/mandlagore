
import unittest
import tempfile
import persistence.db

class TestDB(unittest.TestCase):

    def test_creating_db(self):
        tmp = tempfile.NamedTemporaryFile(suffix='db', prefix='tmp-mdlg')
        db = persistence.db.PersistMandlagore(tmp.name)
        version = db.ensure_schema(rebuilt=True)
        self.assertIsNotNone(version)

