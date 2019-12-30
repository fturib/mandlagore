import unittest.mock
import tempfile
import os
import persistence.db
import services.mandragore_dump_manager

# define the 5 files needed


TEST_FILES = { 'classes.csv': """
".amphibiens"	".amphibiens"
".amphibiens"	"crapaud"
".amphibiens"	"grenouille"
".amphibiens"	"salamandre"
".autres invertébrés (vers,arachnides,insectes...)"	".autres invertébrés (vers,arachnides,insectes...)"
".autres invertébrés (vers,arachnides,insectes...)"	"abeille"
".autres invertébrés (vers,arachnides,insectes...)"	"alcyonaire"
".autres invertébrés (vers,arachnides,insectes...)"	"araignée"
    """,
    'documenturl-gallica.csv': """
53138757-80	https://gallica.bnf.fr/iiif/ark:/12148/btv1b531387571/f80/full/pct:50/0/native.jpg
52504824-10	https://gallica.bnf.fr/iiif/ark:/12148/btv1b52504824c/f10/full/pct:50/0/native.jpg
8453973-65	https://gallica.bnf.fr/iiif/ark:/12148/btv1b8453973c/f65/full/pct:50/0/native.jpg
    """,
    'documenturl-dre.csv': """
7842457-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7842457&E=JPEG&Deb=1&Fin=1&Param=E
7889159-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7889159&E=JPEG&Deb=1&Fin=1&Param=E    
    """, 
    'descriptors-in-scenes.csv': """
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	22540	"faune: abeille"	"abeille (22540)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	27600	"s. ambroise et les abeilles"	"abeille (27600)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	29763	"s. ambroise et les abeilles"	"abeille (29763)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	29905	"pb ja asnat et l'ange"	"abeille (29905)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	40999	"fable: la mouche et l'abeille"	"abeille (40999)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	48701	"faune: oiseau(x)"	"abeille (48701)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	48705	"faune: abeille"	"abeille (48705)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	49298	"faune: abeille"	"abeille (49298)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	51125	"faune: abeille"	"abeille (51125)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	51326	"aristée apiculteur"	"abeille (51326)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	53251	"armes barberini"	"abeille (53251)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	59369	"faune: abeille"	"abeille (59369)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	63132	"faune: abeille"	"abeille (63132)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	65996	"faune: abeille"	"abeille (65996)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	65997	"faune: abeille"	"abeille (65997)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	66855	"apiculture"	"abeille (66855)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	67943	"faune: abeille"	"abeille (67943)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	69903	"faune: abeille"	"abeille (69903)"
643	".autres invertébrés (vers,arachnides,insectes...)"	"abeille"	73161	"armes de maffeo barberini"	"abeille (73161)"
    """,
    'scenes-in-images.csv': """
"10020186-20"	"10020186-20"	"10020186"	"20"
"10020186-20"	"#51326"	"10020186"	"20"
"52504824-10"	"52504824-10"	"10303825"	"1"
"52504824-10"	"#40999"	"10303825"	"1"
"52504824-10"	"#73161"	"10303825"	"1"
    """,
}


class TestViaLabelManager(unittest.TestCase):

    def prepare_data(self, tmpdir: str):
        for k, v in TEST_FILES.items():
            datafile = os.path.join(tmpdir, k)
            with open(datafile, 'w', encoding = 'UTF-8') as content_file:
                content_file.write(v.strip())

    def test_describe_one_scene(self):
        tests = {
            "SELECT * FROM classes": True,
            "SELECT * FROM classes WHERE classID = 'abeille'": True,
            "SELECT * FROM classes WHERE classID = 'lion'": False,
            "SELECT * FROM images WHERE imageID = '7842457-1'": True,
            "SELECT * FROM images WHERE imageID = '52504824-10'": True,
            "SELECT * FROM scenes WHERE mandragoreID = '51326'": True,
            "SELECT * FROM scenes WHERE mandragoreID = 40999 AND imageID = '52504824-10'": True,
            "SELECT * FROM scenes WHERE mandragoreID = 40999 AND imageID = '7842457-1'": False,
            "SELECT * FROM descriptors WHERE classID = 'abeille'": True,
            "SELECT * FROM descriptors WHERE classID = 'abeille' AND mandragoreID = 51125": True,
            "SELECT * FROM descriptors WHERE classID = 'oreilles' AND mandragoreID = 51125": False,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            self.prepare_data(tmpdir)
            with persistence.db.PersistMandlagore(os.path.join(tmpdir, 'mdlg-test.db')) as db:
                db.ensure_schema(True)

                mng = services.mandragore_dump_manager.MandragoreDumpManager(tmpdir, db)

                # now try to import the files
                mng.load_basic_data()

                sqls = [l for l in db.conn.iterdump()]

                # verify some data 
                cur = db.conn.cursor()
                for query, exist in tests.items():
                    cur.execute(query)
                    rows = cur.fetchall()
                    self.assertEqual(exist, len(rows) > 0, "invalid result in request : {} - value {} expect".format(query, exist))
                

        


