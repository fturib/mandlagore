import sqlite3
from sqlite3 import Error
import os
import csv
import typing
from collections import namedtuple


class TableDescription(object):
    def __init__(self, name: str, keys: [], fields: [], links: []):
        super().__init__()
        self.name, self.keys, self.fields = name, keys, fields
        self.all_fields = self.keys + self.fields
        self.links = links

    def insert_or_update_query_full_parameters(self, nameddata: [dict]) -> (str, [[]]):
        return SQLBuilder.build_insert_into_query_with_parameters(self.name,
                                                                  self.all_fields), [[d[n] if n in d else None for n in self.all_fields] for d in nameddata]

    def delete_query_one_parameter(self, paramname, values: []) -> (str, [[]]):
        return SQLBuilder.build_delete_query_with_parameters(self.name, [paramname]), [[d] for d in values]

    def update_query_full_parameters(self, nameddata: [dict]) -> (str, [[]]):
        fields_to_update = list(nameddata[0].keys() - set(self.keys))
        paramnames = fields_to_update + self.keys
        return SQLBuilder.build_update_query_with_parameters(self.name, self.keys, fields_to_update), [[d[n] if n in d else None for n in paramnames] for d in nameddata]

    def get_query_on_keys(self, key_values) -> (str, [[]]):
        return SQLBuilder.build_get_query_with_parameters(self.name, self.keys), [[d] for d in key_values] if len(self.keys) <= 1 else key_values

    def named_data(self, data) -> dict:
        if data is None:
            return None
        if not isinstance(data[0], typing.List):
            return dict(zip(self.all_fields, data))
        else:
            return [dict(zip(self.all_fields, d)) for d in data]

    def qualify(self, field) -> str:
        return "%s.%s" % (self.name, field)

    

TABLES_DESCRIPTIONS = [
    TableDescription('config', [], ['version'], []),
    TableDescription('classes', ['classID'], ['superclassID', 'label'], []),
    TableDescription('mandragores', ['mandragoreID'], ['description'], []),
    TableDescription('images', ['imageID'], ['documentURL', 'width', 'height'], []),
    TableDescription('scenes', ['mandragoreID', 'imageID'], ['x', 'y', 'width', 'height'], [['mandragores', 'mandragoreID'],['images', 'imageID']]),
    TableDescription('descriptors', ['mandragoreID', 'classID'], ['x', 'y', 'width', 'height'], [['mandragores', 'mandragoreID'],['classes', 'classID']]),
]

TABLES = {t.name: t for t in TABLES_DESCRIPTIONS}



GET_IMAGE = '''SELECT * FROM images where imageID = ?'''

MASTER_QUERY = '''SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;'''


IMAGES_OF_LOCALIZED_SCENES = "SELECT images.imageID from images JOIN scenes ON images.imageID = scenes.imageID WHERE scenes.width is not null LIMIT 10"

def keep_unique_items(s:typing.Sequence)->list:
    seen = set()
    return [x for x in s if x not in seen and not seen.add(x)]


class DBException(Exception):
    pass

class SQLBuilder:

    @staticmethod
    def build_where_clause(criterias:tuple) -> str:
        def is_quoted(v):
             return (v[0] == '"' and v[len(v)-1] =='"') or (v[0] == "'" and v[len(v)-1] == "'")
        def quote(v):
            if not isinstance(v, str) or (v is None) or (v =='?') or v.isnumeric() or (v == '') or is_quoted(v):
                return v
            return f"'{v}'"

        def wrap_value(v):        
            if not isinstance(v, str) and (isinstance(v, typing.Sequence)):
                return "( " + ",".join([quote(vl) for vl in v]) +" )"
            return quote(v)
        
        return " AND ".join( ["%s %s %s" % (k, op, '?' if v is None else wrap_value(v)) for k, op, v in criterias])

    @staticmethod
    def build_set_clause(field_and_values:dict) -> str:
        return ", ".join( [f"{f} = {'?' if v is None else v}" for f, v in field_and_values.items()])

    @staticmethod
    def build_select_query(fields: str, tablename: str, criterias:str=None, limit:int=None) -> str:
        sql = f"SELECT {fields} FROM {tablename}"
        if criterias is not None and len(criterias)>0:
            sql += f" WHERE {criterias}"
        if limit is not None:
            sql += f" LIMIT {limit}"
        return sql

    # UPDATE Customers SET ContactName = 'Alfred Schmidt', City= 'Frankfurt' WHERE CustomerID = 1;
    @staticmethod
    def build_update_query(tablename: str, set_fields:str=None, criterias:str=None) -> str:
        sql = f"UPDATE {tablename} SET {set_fields}"
        if criterias is not None and len(criterias)>0:
            sql += f" WHERE {criterias}"
        return sql
    

    @staticmethod
    def build_delete_query(tablename: str, criterias:str=None) -> str:
        sql = f"DELETE FROM {tablename}"
        if criterias is not None:
            sql += f" WHERE {criterias}"
        return sql

    @staticmethod
    def build_insert_into_query(tablename, fields_and_values: dict) -> str:
        fields = ", ".join(fields_and_values.keys())
        values = ", ".join(['"%s"' % v if v is not None else "?" for v in fields_and_values.values()])
        query = "REPLACE INTO %s (%s) VALUES (%s)" % (tablename, fields, values)
        return query

    @staticmethod
    def build_insert_into_query_with_parameters(tablename, fields) -> str:
        fields_and_values = {f: None for f in fields}
        return SQLBuilder.build_insert_into_query(tablename, fields_and_values)

    @staticmethod
    def build_delete_query_with_parameters(tablename, fields) -> str:
        criteria = ((f, '=', None) for f in fields)
        return SQLBuilder.build_delete_query(tablename, SQLBuilder.build_where_clause(criteria))

    @staticmethod
    def build_get_query_with_parameters(tablename, fields) -> str:
        criteria = ((f, '=', None) for f in fields)
        return SQLBuilder.build_select_query("*", tablename, SQLBuilder.build_where_clause(criteria))

    @staticmethod
    def build_update_query_with_parameters(tablename, keys, fields) -> str:
        fields_and_values = {f: None for f in fields}
        criteria = ((f, '=', None) for f in keys)
        return SQLBuilder.build_update_query(tablename, SQLBuilder.build_set_clause(fields_and_values), SQLBuilder.build_where_clause(criteria))

    @staticmethod
    def find_path(from_table:str, to_table:str, tables_viewed:[], maxl = 1000) -> list:
        # just explore the tree of possible until find a path
        ft = TABLES[from_table]
        tt = TABLES[to_table]

        def find_direct_link(ltb, tb):
            for t, f in ltb.links:
                if t == tb.name:
                    return [(ltb.name, t, f)], True
            return [], False

        def find_indirect_link(ltb, tb, unmwanted, append, maxl):
            paths = []
            for t, f in ltb.links:
                if not t in unmwanted:
                    path, found = SQLBuilder.find_path(t, tb.name, unmwanted+[ltb.name], maxl-1)
                    if found:
                        if append:
                            path += [(ltb.name, t, f)]
                        else:
                            path = [(ltb.name, t, f)] + path
                        paths += [path]
                        maxl = min(maxl, len(path))

            for d in TABLES.values():
                if d.name != ltb.name and not d.name in unmwanted:
                    for t, f in d.links:
                        if t == ltb.name:
                            path, found = SQLBuilder.find_path(d.name, tb.name, unmwanted+[t], maxl-1)
                            if found:
                                if append:
                                    path += [(d.name, t, f)]
                                else:
                                    path = [(d.name, t, f)] + path
                                paths += [path]
                                maxl = min(maxl, len(path))

            # return the smallest path
            if len(paths)>0:
                return min(paths), True

            return [], False


        path, found = find_direct_link(ft, tt)
        if found:
            return path, True

        path, found = find_direct_link(tt, ft)
        if found:
            return path, True

        if maxl > 1:
            paths = []
            path, found = find_indirect_link(ft, tt, tables_viewed, False, maxl-1)
            if found:
                paths += [path]
                maxl = min(maxl, len(path))

            path, found = find_indirect_link(tt, ft, tables_viewed, True, maxl-1)
            if found:
                paths += [path]

            # return the smallest path
            if len(paths)>0:
                return min(paths), True

        return [], False

    @staticmethod
    def build_join(source_table:str, needed_tables:list):
        # return the "JOIN xx ON <fields> JOIN xx ON <fields> .. etc"
        # compute the right fields, based on the primary keys (simplified)
        # we need to compute any missing link between the tables
        tb = TABLES[source_table]

        # find an order in the join and add the missing tables to ensure all links
        links = []
        missing = set(needed_tables)
        missing.discard(source_table)
        query = source_table

        if len(missing)==0:
            return query

        # Need to compute the join with missing tables

        for t in missing:
            path, found = SQLBuilder.find_path(source_table, t, [])
            if not found:
                raise DBException(f"cannot join the tables {source_table} and {t}")
            
            # add to joined all unknwon paths
            links += [p for p in path if not p in links and not (p[1], p[0], p[2]) in links]

        sql = " JOIN %s ON (%s)"
        joined = set([source_table])
        for (ts, td, f) in links:
            stb = TABLES[ts]
            dtb = TABLES[td]
            # need to add the table that is needed, unless it is already in
            if ts in joined and td in joined:
                raise DBException(f"Invalid joined operation - tables {ts} and {td} are already joined")
            tadd = td if ts in joined else ts if td in joined else ts if ts in needed_tables else td if td in needed_tables else ts
            crit = SQLBuilder.build_where_clause([(stb.qualify(f), '=', dtb.qualify(f))])
            query += sql % (tadd, crit)
            joined.add(tadd)

        # Verify we have all the tables expected and raise error if not
        unjoined = set(needed_tables) - joined
        if len(unjoined) > 0:
            raise DBException(f"Was not able to join all needed tables - these tables are missing in the join : {unjoined}")

        return query

    @staticmethod
    def build_field_criteria(table, field_filter, field_values) -> tuple:
        td = TABLES[table]
        parts = field_filter.split(":")
        fieldname = parts[0]
        operator = '='
        if fieldname == "ID":
            fields = td.keys
            values = field_values
            if len(fields)==1:
                values = (values,)
        elif fieldname == "localized":
            fields = ['width','height']
            values = ['not null'] * 2
            operator = 'is'
        else:
            fields = (fieldname,)
            values = (field_values,)
        
        if len(parts)>1:
            if parts[1] == "like":
                operator = 'like'
            elif parts[1] == "list":
                operator = 'in'
        
        return tuple(zip([td.qualify(f) for f in fields], [operator] * len(fields), values))
        


    @staticmethod
    def build_filtered_query(table, fields, filters, limit=None, qualify_fields=True):
        # Build a QUEY that retreive imagesIDs that match corresponding filters
        # filters : a triplet (table, field-like, value) where:
        #  - table is in one of the tables names
        #  - field-like can be "ID" (for all fields) or field of table with "-like", "-list", in suffix, or "localized" 
        #  - value is either a direct value (string), a like value (string), or tuple of values (for -list)
        # all filters are AND-ed
        # limit, if defined, provide the number of elements to return

        # "SELECT images.imageID from images JOIN scenes ON images.imageID = scenes.imageID WHERE scenes.width is not null LIMIT 10"
        tb = TABLES[table]

        criterias = []
        for (t, f, v) in filters:
            criterias.extend(SQLBuilder.build_field_criteria(t, f, v))
        
        tables = SQLBuilder.build_join(table, [f[0] for f in filters])
        fieldclause = ""
        if qualify_fields:
            fieldclause = ", ".join(tb.qualify(f) for f in fields) 
        else:
            fieldclause = ", ".join(f for f in fields) 
        whereclause = SQLBuilder.build_where_clause(criterias)

        query = SQLBuilder.build_select_query(fieldclause, tables, whereclause, limit)
        
        return query
        


class DBOperationHelper:

    MULTI_RECORD = 'multi-records'
    SINGLE_RECORD = 'single-record'

    def __init__(self, conn):
        self.conn = conn

    def delete_records(self, tablename, criterias: dict):
        sql = SQLBuilder.build_delete_records_query(tablename, criterias)
        self.conn.execute(sql)

    def insert_into(self, tablename, fieldsAndValues: dict):
        query = SQLBuilder.build_insert_into_query(tablename, fieldsAndValues)
        self.conn.execute(query)

    def create_schema(self, schema_filename):
        # check the version of current schema
        # if not existent, then create tables using SQL schema file
        content = ""
        with open(schema_filename, 'r') as content_file:
            content = content_file.read()
        self.conn.executescript(content)

    def import_csv_file(self, filename, insertQuery, fieldlist, rowTranslater=None) -> (str, []):
        # sql = INSERT INTO table(field, field, ...) VALUES(?,?, ...)
        # fieldlist is an ordered set of the numbers of fields to be taken from file to the query - 0 is first index
        # TODO manage exceptions

        lines = 0
        warnings = []
        with open(filename, newline='', encoding='utf-8') as csvfile:
            csvreader = csv.reader(csvfile, delimiter='\t', quotechar='"')
            cur = self.conn.cursor()
            for row in csvreader:
                frow, skip = rowTranslater(row) if rowTranslater is not None else (row, False)
                if not skip:
                    data = frow if fieldlist is None else [frow[x] for x in fieldlist]
                    try:
                        cur.execute(insertQuery, data)
                        lines += 1
                    except Exception as e:
                        warnings.append("%s : the line (%s) could not be imported : %s" % (filename, ",".join(data), str(e)))
        self.conn.commit()
        return "%d lines imported" % lines, warnings

    def import_csv_mode_file(self, filename, insertQuery, encoding, delim, mode, fieldlist, rowTranslater=None) -> (str, []):
        # sql = INSERT INTO table(field, field, ...) VALUES(?,?, ...)
        # fieldlist is an ordered set of the numbers of fields to be taken from file to the query - 0 is first index
        # TODO manage exceptions

        lines = 0
        warnings = []
        with open(filename, newline='', encoding=encoding) as csvfile:
            csvreader = csv.reader(csvfile, delimiter=delim)
            cur = self.conn.cursor()
            for line in csvreader:
                rows = [[line[0], x] for x in line[1:]] if mode == DBOperationHelper.MULTI_RECORD else [line]
                for row in rows:
                    frow, skip = rowTranslater(row) if rowTranslater is not None else (row, False)
                    if not skip:
                        data = frow if fieldlist is None else [frow[x] for x in fieldlist]
                        try:
                            cur.execute(insertQuery, data)
                        except Exception as e:
                            warnings.append("%s : the line (%s) could not be imported : %s" % (filename, ",".join(data), str(e)))
                lines += 1

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
        self.conn.commit()

    def ensure_images(self, images_id_url_w_h: [dict]):
        # images_id_url_w_h is a list of dict(). Each dict has the names of fields as keys
        q, p = TABLES['images'].insert_or_update_query_full_parameters(images_id_url_w_h)
        self.conn.executemany(q, p)
        self.conn.commit()

    def update_images(self, images_id_w_h: [dict]):
        # images_id_url_w_h is a list of dict(). Each dict has the names of fields as keys
        q, p = TABLES['images'].update_query_full_parameters(images_id_w_h)
        self.conn.executemany(q, p)
        self.conn.commit()

    def add_scenes(self, scenes: [dict]):
        q, p = TABLES['scenes'].insert_or_update_query_full_parameters(scenes)
        self.conn.executemany(q, p)
        self.conn.commit()

    def add_descriptors(self, descriptors):
        q, p = TABLES['descriptors'].insert_or_update_query_full_parameters(descriptors)
        self.conn.executemany(q, p)
        self.conn.commit()

    def retrieve_image(self, imageID):
        query, data = TABLES['images'].get_query_on_keys([imageID])
        return TABLES['images'].named_data(self.conn.execute(query, data[0]).fetchone())

    def retrieve_images(self, fields, filters, limit=None):
        # Build a QUEY that retreive imagesIDs that match corresponding filters
        # filters : a triplet (table, field-like, value) where:
        #  - table is in 'images', 'scenes', 'descriptors'
        #  - field-like can be "ID" or field of table with "-like", "-list", in suffix, or "localized" 
        #  - value is either a direct value (string), a like value (string), or tuple of values (for -list)
        #
        # limit, if defined, provide the number of elements to return

        # "SELECT images.imageID from images JOIN scenes ON images.imageID = scenes.imageID WHERE scenes.width is not null LIMIT 10"

        td = TABLES['images']        
        query = SQLBuilder.build_filtered_query(td.name, fields, filters, limit)
        queryCount = SQLBuilder.build_filtered_query(td.name, ("COUNT(*)",), filters, qualify_fields=False)
        total = self.conn.execute(queryCount).fetchone()[0]
        if limit is not None:
            total = min(total, limit)
        return self.conn.execute(query), total

    def schema_version(self):
        if self.version is None:
            for r in self.conn.execute("SELECT version FROM config"):
                self.version = r[0]
        return self.version
