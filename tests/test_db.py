
import unittest
import tempfile
from mdlg.persistence.db import PersistMandlagore, SQLBuilder, DBException


class TestDB(unittest.TestCase):
    def test_creating_db(self):
        tmp = tempfile.NamedTemporaryFile(suffix='db', prefix='tmp-mdlg')
        with PersistMandlagore(tmp.name) as db:
            version = db.ensure_schema(rebuilt=True)
            self.assertIsNotNone(version)

    def test_fetching_image(self):
        IMAGE = {'imageID': 'name-page', 'documentURL': 'http://localhist:8080/whatever', 'width': 1000, 'height': 2000}
        tmp = tempfile.NamedTemporaryFile(suffix='db', prefix='tmp-mdlg')
        with PersistMandlagore(tmp.name) as db:
            version = db.ensure_schema(rebuilt=True)
            self.assertIsNotNone(version)
            db.ensure_images([IMAGE])
            data = db.retrieve_image(IMAGE['imageID'])
            self.assertTrue(len(data), 1)

    def test_updating_image(self):
        IMAGE = {'imageID': 'name-page', 'documentURL': 'http://localhist:8080/whatever', 'width': 1000, 'height': 2000}
        tmp = tempfile.NamedTemporaryFile(suffix='db', prefix='tmp-mdlg')
        with PersistMandlagore(tmp.name) as db:
            version = db.ensure_schema(rebuilt=True)
            self.assertIsNotNone(version)
            db.ensure_images([IMAGE])
            
            data = db.retrieve_image(IMAGE['imageID'])
            self.assertTrue(len(data), 1)
            self.assertEqual(data, IMAGE) 

            IMAGE_UPDATE = {'imageID': 'name-page', 'width': 5, 'height': 40}
            db.update_images([IMAGE_UPDATE])

            IMAGE_UPDATED = IMAGE
            IMAGE_UPDATED.update(IMAGE_UPDATE)
            data = db.retrieve_image(IMAGE['imageID'])
            self.assertTrue(len(data), 1)
            self.assertEqual(data, IMAGE_UPDATED)


class TestSQLHelper(unittest.TestCase):


    def test_find_path(self):

        TESTS = {
            'double-join': [('images', 'descriptors', []), ([('scenes', 'images', 'imageID'), ('scenes', 'mandragores', 'mandragoreID'), ('descriptors', 'mandragores', 'mandragoreID')], True)],
            'empty-join': [('images', 'config', []), ([], False)],
            'simple-join': [('images', 'scenes', []), ([('scenes', 'images', 'imageID')], True)],
            'double-join-limited': [('images', 'descriptors', ['scenes']), ([], False)],
        } 

        for name, t in TESTS.items():
            params, exp_results = t
            paths, found = SQLBuilder.find_path(*params)
            exp_paths, exp_found = exp_results
            self.assertEqual(found, exp_found)
            self.assertSetEqual(set(paths), set(exp_paths), )

    def test_build_filtered_query(self):

        TEST = {
            'one-query-simple-where' : [(('images', 'ID', '"an-of-an-image"'),), False],
            'dbl-join-query-simple-where-localized' : [(('scenes', 'localized', None),('images', 'ID:like', '"%images-names"'), ('descriptors', 'ID:list', (('"m-one"', '"m-two"'),('"class-two"','"class-one"')),)), False],
            'one-query-no-where' : [(), True],
            'one-query-simple-where-field' : [[('images', 'height', 14)], False],
            'one-query-simple-where-like' : [(('images', 'ID:like', '"%images-names"'),), False],
            'one-query-simple-where-list' : [(('images', 'ID:list', ['"id-1"','"id-2"','"id-3"']),), False],
            'one-query-simple-where-localized' : [(('images', 'localized', None),), False],
            'sev-query-simple-where-localized' : [(('images', 'localized', None),('images', 'ID:like', ['"%images-names"'])), False],
            'join-query-simple-where-localized' : [(('scenes', 'localized', None),('images', 'ID:like', ('"%images-names"'),)), False],
        }
        tmp = tempfile.NamedTemporaryFile(suffix='db', prefix='tmp-mdlg')
        with PersistMandlagore(tmp.name) as db:
            version = db.ensure_schema(rebuilt=True)
            self.assertIsNotNone(version)

            for k, ts in TEST.items():
                sql = SQLBuilder.build_filtered_query('images', '*', ts[0], limit=None)
                try:
                    db.conn.execute(sql)
                except Exception as e:
                    self.fail("%s - query %s failed : %s " % (k, sql, str(e)))
    