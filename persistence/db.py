
import sqlite3
from sqlite3 import Error
import os
import csv

DELETE_SCENES = '''DELETE * FROM scenes WHERE mandragoreID = ?'''
DELETE_DESCRIPTORS = '''DELETE * FROM descriptors WHERE mandragoreID = ?'''
GET_IMAGE = '''SELECT * FROM images where imageID = ?'''
INSERT_IMAGE = '''INSERT INTO images (imageID, documentURL, width, height) VALUES (?, ?, ?, ?)'''
INSERT_SCENE = '''INSERT INTO scenes (mandragoreID, imageID, x, y, width, height) VALUES (?, ?, ?, ?, ?, ?)'''
INSERT_DESCRIPTOR = '''INSERT INTO descriptors (mandragoreID, classID, x, y, width, height) VALUES (?, ?, ?, ?, ?, ?)'''


class SQLBuilder:

    @staticmethod
    def build_where_clause(criterias) -> str:
        criteria = ""
        for k, v in criterias.items():
            criteria = criteria + " AND " if len(criteria)>0 else "" + ("%s = %s" % k, v)
        return criteria

    @staticmethod
    def build_delete_records_query(tablename, criterias) -> str:
        sql = "DELETE * FROM %s" % tablename
        crit = SQLBuilder.build_where_clause(criterias)
        if len(crit) > 0:
            sql = "%s WHERE %s" % sql, crit
        return sql

    @staticmethod
    def build_insert_into_query(tablename, fields_and_values) -> str:
        fields = ""
        values = ""
        for (k, v) in fields_and_values:
            fields += ("" if len(fields) == 0 else ", ") + k
            values += ("" if len(values) == 0 else ", ") + ('"%s"' % v if v is not None else "?")

        query = "INSERT INTO %s (%s) VALUES (%s)" % (tablename, fields, values)
        return query

    @staticmethod
    def build_insert_into_query_with_parameters(tablename, fields) -> str:
        fields_and_values = [(f, None) for f in fields]
        return SQLBuilder.build_insert_into_query(tablename, fields_and_values)

class DBOperationHelper:

    def __init__(self, conn):
        self.conn = conn

    def delete_records(self, tablename, criterias):
        sql = SQLBuilder.build_delete_records_query(tablename, criterias)
        self.conn.execute(sql)

    def insert_into(self, tablename, fieldsAndValues):
        query = SQLBuilder.build_insert_into_query(tablename, fieldsAndValues)
        self.conn.execute(query)

    def create_schema(self, schema_filename):
        # check the version of current schema
        # if not existent, then create tables using SQL schema file
        content = ""
        with open(schema_filename, 'r') as content_file:
            content = content_file.read()
        self.conn.executescript(content)

    def import_csv_file(self, filename, insertQuery, fieldlist, rowTranslater = None):
        # sql = INSERT INTO table(field, field, ...) VALUES(?,?, ...)
        # fieldlist is an ordered set of the numbers of fields to be taken from file to the query - 0 is first index
        #TODO manage exceptions
        with open(filename, newline='', encoding='UTF-8') as csvfile:
            csvreader = csv.reader(csvfile, delimiter='\t', quotechar='"')
            cur = self.conn.cursor()
            for row in csvreader:
                frow, skip = rowTranslater(row) if rowTranslater is not None else (row, False)
                if not skip:
                    cur.execute(insertQuery, row if fieldlist is None else [frow[x] for x in fieldlist])
        self.conn.commit()



class PersistMandlagore:

    def __init__(self, filename=None):
        self.version = None
        self.conn = None
        if filename is not None:
            self.connect(filename)

    def _ensure_disconnect(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def connect(self, filename):
        """ create a database connection to a SQLite database """
        self._ensure_disconnect()
        try:
            self.conn = sqlite3.connect(filename)
            print(sqlite3.version)
        except Error as e:
            print(e)
            raise e

    def __del__(self):
        self._ensure_disconnect()

    def ensure_schema(self, rebuilt: bool) -> str:
        # check the version of current schema
        # if not existent, then create tables using SQL schema file

        if rebuilt or self.schema_version() is None:
            persistence_dir = os.path.dirname(os.path.realpath(__file__))
            schema_filename = os.path.join(persistence_dir, "mandlagore.db.schema.sql")
            self.version = None
            DBOperationHelper(self.conn).create_schema(schema_filename)

        return self.schema_version()


    def delete_mandragore_related(self, mandragore_ids):
        self.conn.cursor().executemany(DELETE_SCENES, mandragore_ids)
        self.conn.cursor().executemany(DELETE_DESCRIPTORS, mandragore_ids)

    def ensure_images(self, images_id_url_w_h):
        self.conn.cursor().executemany(INSERT_IMAGE, images_id_url_w_h)

    def add_scenes(self, scenes):
        self.conn.cursor().executemany(INSERT_SCENE, scenes)

    def add_descriptors(self, descriptors):
        self.conn.cursor().executemany(INSERT_DESCRIPTOR, descriptors)

    def retrieve_image(self, imageID):
        self.conn.cursor().execute(GET_IMAGE, imageID)
        return self.conn.cursor().fetchone()

    def schema_version(self):
        if self.version is None:
            for r in self.conn.execute("SELECT version FROM config"):
                self.version = r[0]
        return self.version
