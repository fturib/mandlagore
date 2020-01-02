import os
from mdlg.persistence.db import DBOperationHelper, PersistMandlagore, DBOperationHelper, SQLBuilder
import collections


def _classes_csv_preprocess(row) -> (list, bool):
    return row, row[0] == row[1]


def _scene_in_images_csv_preprocess(row) -> (list, bool):
    skip = row[0] == row[1]
    row[1] = row[1][1:]
    return row, skip

def _descriptor_image_csv_preprocess(row) -> (list, bool):
    row[1] = row[1][1:]
    return row, False

def _descriptor_classe_csv_preprocess(row) -> (list, bool):
    skip = len(row[1]) <= 0
    return (row[0][1:], row[1].split(' ')[0]), skip


class MandragoreDumpManager:
    # metadata.zip contains - IT IS NOT USED HERE
    # - a folder "metadata" that contains:
    #   - "metadata/Zoologie-images-notices.csv" - ; sep - encoding ? - each line is pageID -> set of mandragoreID
    #   - "metadata/Zoologie-notices-descripteurs.csv" - ; sep - encoding ? - each line is mandragoreID -> set of classes
    #   - "metadata/Zoologie-notices-superclasse.csv" - ; sep - encoding ? - each line is mandragoreID -> one superclasse - HOW TO USE IT ?
    #   - "metadata/Zoologie-URLs-DRE-Mandragore.txt" - TAB sep - each line is pageID -> URL in DRE remoteDB
    #   - "metadata/Zoologie-URLs-Gallica.txt" - TAB sep - each line is pageID -> URL in GALACTICA remoteDB

    # files for initializing the DB will be: (in folder metadata)
    #  - classes.csv
    #  - descriptors-in-scenes.csv
    #  - scenes-in-images.csv
    #  - documenturl-gallica.csv
    #  - documenturl-dre.csv

    # all are Tab separated values. " is the string delimitor. Encoding is UTF8

    DUMP_DATA = {
        'classes.csv': {
            'table': "classes",
            'fields': ["classID", "superclassID"],
            # ".autres invertébrés (vers,arachnides,insectes...)"	"abeille"
            # need to jump equal row where fields are equals
            'csv' : [1,0],
            'preprocess' : _classes_csv_preprocess
        },
        'documenturl-gallica.csv': {
            'table': "images",
            'fields': ["imageID", "documentURL"],
            # 53138757-80	https://gallica.bnf.fr/iiif/ark:/12148/btv1b531387571/f80/full/pct:50/0/native.jpg
            'csv': [0, 1],
            'preprocess': None,
        },
        'documenturl-dre.csv': {
            'table': "images",
            'fields': ["imageID", "documentURL"],
            # 7842457-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7842457&E=JPEG&Deb=1&Fin=1&Param=E
            'csv': [0, 1],
            'preprocess': None,
        },
        'scenes-in-images.csv': {
            'table': "scenes",
            'fields': ["mandragoreID", "imageID"],
            # "10020186-20"	"#209699"	"10020186"	"20"
            # need to skip equal fields, need to remove the '#' in front of the mandragoreID
            'csv': [1, 0],
            'preprocess': _scene_in_images_csv_preprocess,
        },
        'descriptors-in-scenes.csv': {
            'table': "descriptors",
            'fields': ["mandragoreID", "classID"],
            # 643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	51125	"faune: abeille"	"abeille (51125)"
            'csv': [3, 2],
            'preprocess': None,
        },
    }


    BnfDumpData = collections.namedtuple('BnfDumpData', ['filename', 'encoding', 'table', 'fields', 'mode', 'columns', 'delimiter', 'transform'])
    BNF_DUMP_DATA = [
        # 53138757-80	https://gallica.bnf.fr/iiif/ark:/12148/btv1b531387571/f80/full/pct:50/0/native.jpg
        BnfDumpData('Zoologie-URLs-Gallica.txt', 'utf-8', "images",["imageID", "documentURL"], 
        DBOperationHelper.SINGLE_RECORD, [0, 1], '\t', None),

        # 7842457-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7842457&E=JPEG&Deb=1&Fin=1&Param=E
        BnfDumpData('Zoologie-URLs-DRE-Mandragore.txt', 'utf-8', "images",["imageID", "documentURL"], 
        DBOperationHelper.SINGLE_RECORD, [0, 1], '\t', None),

        # 10507217-143;#78047;#78048;#78049;#78050
        BnfDumpData('Zoologie-images-notices.csv', 'latin_1', "scenes",["mandragoreID", "imageID"],
        DBOperationHelper.MULTI_RECORD, [1, 0], ';',_descriptor_image_csv_preprocess),

        # 100327;chien (100327);faucon (100327);oiseau (100327);perdrix (100327);
        BnfDumpData('Zoologie-notices-descripteurs.csv',  'latin_1', "descriptors",["mandragoreID", "classID"],
        DBOperationHelper.MULTI_RECORD, [0, 1],';', _descriptor_classe_csv_preprocess),

        # 100327;chien (100327);faucon (100327);oiseau (100327);perdrix (100327);
        BnfDumpData('Zoologie-notices-descripteurs.csv',  'latin_1', "classes", ["classID"], 
        DBOperationHelper.MULTI_RECORD, [1], ';', _descriptor_classe_csv_preprocess),
    ]


    def __init__(self, rootdir: str, persistance: PersistMandlagore):
        self.rootdir = rootdir
        self.persistance = persistance
        pass

    def load_basic_data(self) -> ():
        # We suppose the DB is ready and cleaned

        imported = []
        dbHelper = DBOperationHelper(self.persistance.conn)
        for doc, params in self.DUMP_DATA.items():
            full_docname = os.path.join(self.rootdir, doc)
            if not (os.path.exists(full_docname) and os.path.isfile(full_docname)):
                # need to warn the file is not processed
                raise FileNotFoundError("Cannot import basic data as file {} is mising.".format(full_docname))
            query = SQLBuilder.build_insert_into_query_with_parameters(params["table"], params["fields"])
            report, warnings = dbHelper.import_csv_file(full_docname, query, params["csv"], params["preprocess"])
            imported.append((doc, report, warnings))
        return imported

    def load_bnf_data(self) -> ():
        # We suppose the DB is ready and cleaned

        imported = []
        dbHelper = DBOperationHelper(self.persistance.conn)
        for filename, encoding, tablename, fields, record_mode, columns, delim, transform in self.BNF_DUMP_DATA:
            full_docname = os.path.join(self.rootdir, filename)
            if not (os.path.exists(full_docname) and os.path.isfile(full_docname)):
                # need to warn the file is not processed
                raise FileNotFoundError("Cannot import basic data as file {} is mising.".format(full_docname))
            query = SQLBuilder.build_insert_into_query_with_parameters(tablename, fields)
            report, warnings = dbHelper.import_csv_mode_file(full_docname, query, encoding, delim, record_mode, columns, transform)
            imported.append((filename, report, warnings))
        return imported





