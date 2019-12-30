
import sqlite3
from sqlite3 import Error
import os
import csv
import typing
from collections import namedtuple

class TableDescription(object):

    def __init__(self, name:str, keys:[], fields:[]):
        super().__init__()
        self.name, self.keys, self.fields = name, keys, fields
        self.all_fields = self.keys + self.fields

    def update_query_full_parameters(self, nameddata: [dict]) -> (str, [[]]):
        return SQLBuilder.build_insert_into_query_with_parameters(self.name, self.all_fields),  [[d[n] if n in d else 'NULL' for n in self.all_fields] for d in nameddata]

    def delete_query_one_parameter(self, paramname, values:[]) -> (str, [[]]):
        return SQLBuilder.build_delete_query_with_parameters(self.name, [paramname]),  [[d] for d in values]

    def get_query_on_keys(self, key_values) -> (str, [[]]):
        return SQLBuilder.build_get_query_with_parameters(self.name, self.keys),  [[d] for d in key_values] if len(self.keys)<=1 else key_values

    def named_data(self, data) -> dict:
        if data is None:
            return None
        if not isinstance(data[0], typing.List):
            return dict(zip(self.all_fields, data))
        else:
            return [dict(zip(self.all_fields, d)) for d in data]



TABLES_DESCRIPTIONS = [
    TableDescription('config', [], ['version']),
    TableDescription('classes', ['classID'], ['superclassID', 'label']),
    TableDescription('mandragores', ['imageID'], ['description']),
    TableDescription('images', ['imageID'], ['documentURL', 'width', 'height']),
    TableDescription('scenes', ['mandragoreID', 'imageID'], ['x', 'y', 'width', 'height']),
    TableDescription('descriptors', ['mandragoreID', 'classID'], ['x', 'y', 'width', 'height']),
]

TABLES = {t.name: t for t in TABLES_DESCRIPTIONS}

GET_IMAGE = '''SELECT * FROM images where imageID = ?'''

MASTER_QUERY = '''SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;'''

class SQLBuilder:

    @staticmethod
    def build_where_clause(criterias) -> str:
        criteria = ""
        for k, v in criterias.items():
            criteria = criteria + " AND " if len(criteria)>0 else "" + ("%s = %s" % (k, '?' if v is None else v))
        return criteria

    @staticmethod
    def build_where_clause_query(fetch: str, tablename:str, criterias: dict) -> str:
        sql = "%s FROM %s" % (fetch, tablename)
        crit = SQLBuilder.build_where_clause(criterias)
        if len(crit) > 0:
            sql = "%s WHERE %s" % (sql, crit)
        return sql


    @staticmethod
    def build_insert_into_query(tablename, fields_and_values: dict) -> str:
        fields = ""
        values = ""
        for k, v in fields_and_values.items():
            fields += ("" if len(fields) == 0 else ", ") + k
            values += ("" if len(values) == 0 else ", ") + ('"%s"' % v if v is not None else "?")

        query = "REPLACE INTO %s (%s) VALUES (%s)" % (tablename, fields, values)
        return query

    @staticmethod
    def build_insert_into_query_with_parameters(tablename, fields) -> str:
        fields_and_values = {f: None for f in fields}
        return SQLBuilder.build_insert_into_query(tablename, fields_and_values)

    @staticmethod
    def build_delete_query_with_parameters(tablename, fields) -> str:
        criteria = {f: None for f in fields}
        return SQLBuilder.build_where_clause_query("DELETE", tablename, criteria)

    @staticmethod
    def build_get_query_with_parameters(tablename, fields) -> str:
        criteria = {f: None for f in fields}
        return SQLBuilder.build_where_clause_query("SELECT *", tablename, criteria)

class DBOperationHelper:

    def __init__(self, conn):
        self.conn = conn

    def delete_records(self, tablename, criterias:dict ):
        sql = SQLBuilder.build_delete_records_query(tablename, criterias)
        self.conn.execute(sql)

    def insert_into(self, tablename, fieldsAndValues:dict):
        query = SQLBuilder.build_insert_into_query(tablename, fieldsAndValues)
        self.conn.execute(query)

    def create_schema(self, schema_filename):
        # check the version of current schema
        # if not existent, then create tables using SQL schema file
        content = ""
        with open(schema_filename, 'r') as content_file:
            content = content_file.read()
        self.conn.executescript(content)

    def import_csv_file(self, filename, insertQuery, fieldlist, rowTranslater = None) -> (str, []):
        # sql = INSERT INTO table(field, field, ...) VALUES(?,?, ...)
        # fieldlist is an ordered set of the numbers of fields to be taken from file to the query - 0 is first index
        #TODO manage exceptions

        lines = 0
        warnings = []
        with open(filename, newline='', encoding='utf-8') as csvfile:
            csvreader = csv.reader(csvfile, delimiter='\t', quotechar='"')
            cur = self.conn.cursor()
            for row in csvreader:
                frow, skip = rowTranslater(row) if rowTranslater is not None else (row, False)
                if not skip:
                    data = row if fieldlist is None else [frow[x] for x in fieldlist]
                    try:
                        cur.execute(insertQuery, data)
                        lines += 1
                    except Exception as e:
                        warnings.append("%s : the line (%s) could not be imported : %s" % (filename, ",".join(data), str(e)))
        self.conn.commit()
        return "%d lines imported" % lines, warnings



class PersistMandlagore(object):

    def __init__(self, filename=None):
        self.version = None
        self.conn = None
        if filename is not None:
            self.connect(filename)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._ensure_disconnect()

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
        q, d = TABLES['scenes'].delete_query_one_parameter('mandragoreID', mandragore_ids)
        self.conn.executemany(q, d)
        q, d = TABLES['descriptors'].delete_query_one_parameter('mandragoreID', mandragore_ids)
        self.conn.executemany(q, d)

    def ensure_images(self, images_id_url_w_h: [dict]):
        # images_id_url_w_h is a list of dict(). Each dict has the names of fields as keys
        self.conn.executemany(*TABLES['images'].update_query_full_parameters(images_id_url_w_h))

    def add_scenes(self, scenes: [dict]):
        self.conn.executemany(*TABLES['scenes'].update_query_full_parameters(scenes))

    def add_descriptors(self, descriptors):
        self.conn.executemany(*TABLES['descriptors'].update_query_full_parameters(descriptors))

    def retrieve_image(self, imageID):
        query, data = TABLES['images'].get_query_on_keys([imageID])
        return TABLES['images'].named_data(self.conn.cursor().execute(query, data[0]).fetchone())
    
    def schema_version(self):
        if self.version is None:
            for r in self.conn.execute("SELECT version FROM config"):
                self.version = r[0]
        return self.version
