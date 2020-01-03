import unittest
import tempfile
import os
from mdlg.persistence.db import PersistMandlagore
from mdlg.services.mandragore_dump_manager import MandragoreDumpManager

# define the 5 files needed

TEST_FILES = {
    'classes.csv':
    """
".amphibiens"	".amphibiens"
".amphibiens"	"crapaud"
".amphibiens"	"grenouille"
".amphibiens"	"salamandre"
".autres invertébrés (vers,arachnides,insectes...)"	".autres invertébrés (vers,arachnides,insectes...)"
".autres invertébrés (vers,arachnides,insectes...)"	"abeille"
".autres invertébrés (vers,arachnides,insectes...)"	"alcyonaire"
".autres invertébrés (vers,arachnides,insectes...)"	"araignée"
    """,
    'documenturl-gallica.csv':
    """
53138757-80	https://gallica.bnf.fr/iiif/ark:/12148/btv1b531387571/f80/full/pct:50/0/native.jpg
52504824-10	https://gallica.bnf.fr/iiif/ark:/12148/btv1b52504824c/f10/full/pct:50/0/native.jpg
8453973-65	https://gallica.bnf.fr/iiif/ark:/12148/btv1b8453973c/f65/full/pct:50/0/native.jpg
    """,
    'documenturl-dre.csv':
    """
7842457-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7842457&E=JPEG&Deb=1&Fin=1&Param=E
7889159-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7889159&E=JPEG&Deb=1&Fin=1&Param=E
    """,
    'descriptors-in-scenes.csv':
    """
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
    'scenes-in-images.csv':
    """
"10020186-20"	"10020186-20"	"10020186"	"20"
"10020186-20"	"#51326"	"10020186"	"20"
"52504824-10"	"52504824-10"	"10303825"	"1"
"52504824-10"	"#40999"	"10303825"	"1"
"52504824-10"	"#73161"	"10303825"	"1"
    """,
}

TEST_BNF_FILES = {
    'Zoologie-URLs-Gallica.txt':
    """
10303825-1	https://gallica.bnf.fr/iiif/ark:/12148/btv1b531387571/f80/full/pct:50/0/native.jpg
10308906-65	https://gallica.bnf.fr/iiif/ark:/12148/btv1b53138776d/f23/full/pct:50/0/native.jpg
52504824-10	https://gallica.bnf.fr/iiif/ark:/12148/btv1b52504824c/f10/full/pct:50/0/native.jpg
52504824-22	https://gallica.bnf.fr/iiif/ark:/12148/btv1b52504824c/f22/full/pct:50/0/native.jpg
52504824-26	https://gallica.bnf.fr/iiif/ark:/12148/btv1b52504824c/f26/full/pct:50/0/native.jpg
52504824-45	https://gallica.bnf.fr/iiif/ark:/12148/btv1b52504824c/f45/full/pct:50/0/native.jpg
52504824-100	https://gallica.bnf.fr/iiif/ark:/12148/btv1b52504824c/f100/full/pct:50/0/native.jpg
52504824-151	https://gallica.bnf.fr/iiif/ark:/12148/btv1b52504824c/f151/full/pct:50/0/native.jpg
52504824-173	https://gallica.bnf.fr/iiif/ark:/12148/btv1b52504824c/f173/full/pct:50/0/native.jpg
""",
    'Zoologie-URLs-DRE-Mandragore.txt':
    """
10020186-20	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7864859&E=JPEG&Deb=1&Fin=1&Param=E
10500687-10	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7823254&E=JPEG&Deb=1&Fin=1&Param=E
10500687-11	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7823255&E=JPEG&Deb=1&Fin=1&Param=E
10500687-147	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7823262&E=JPEG&Deb=1&Fin=1&Param=E
7823263-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7823263&E=JPEG&Deb=1&Fin=1&Param=E
7823264-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7823264&E=JPEG&Deb=1&Fin=1&Param=E
7823268-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7823268&E=JPEG&Deb=1&Fin=1&Param=E
7823269-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7823269&E=JPEG&Deb=1&Fin=1&Param=E
7823277-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7823277&E=JPEG&Deb=1&Fin=1&Param=E
7823219-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7823219&E=JPEG&Deb=1&Fin=1&Param=E
7823280-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7823280&E=JPEG&Deb=1&Fin=1&Param=E
7823291-1	http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-7823291&E=JPEG&Deb=1&Fin=1&Param=E
""",
    'Zoologie-notices-descripteurs.csv':
    """
#100001;oiseau (100001);vache (100001);
#100024;cheval (100024);
#100026;cheval (100026);
#100027;cheval (100027);
#209699;cheval (209699);
#100038;serpent (100038);
#100044;lion (100044);
#10005;taureau (10005);
#206805;cheval (206805);
#100057;cerf (100057);lion (100057);
#181563;serpent (181563);
#52930;taureau (52930);
#10009;biche (10009);cerf (10009);
#100105;oiseau (100105);
#100112;cheval (100112);
#52932;poisson (52932);
#52957;loup (52957);tortue (52957);
""",
    'Zoologie-images-notices.csv':
    """
10020186-20;#209699
10303825-1;#206804;#206805
10308906-65;#181563
10500687-10;#52930
10500687-11;#52932;#52933
10500687-147;#52957
""",
}


class TestViaLabelManager(unittest.TestCase):
    def prepare_data(self, tmpdir: str, files):
        for k, v in files.items():
            datafile = os.path.join(tmpdir, k)
            with open(datafile, 'w', encoding='UTF-8') as content_file:
                content_file.write(v.strip())

    def verify_db_content(self, db, totests):
        sqls = [l for l in db.conn.iterdump()]

        # verify some data
        cur = db.conn.cursor()
        for query, exist in totests.items():
            cur.execute(query)
            rows = cur.fetchall()
            self.assertEqual(
                exist,
                len(rows) > 0,
                "invalid result in request : {} - value {} expect".format(
                    query, exist))

    def test_reorganized_dumps(self):
        queries = {
            "SELECT * FROM classes":
            True,
            "SELECT * FROM classes WHERE classID = 'abeille'":
            True,
            "SELECT * FROM classes WHERE classID = 'lion'":
            False,
            "SELECT * FROM images WHERE imageID = '7842457-1'":
            True,
            "SELECT * FROM images WHERE imageID = '52504824-10'":
            True,
            "SELECT * FROM scenes WHERE mandragoreID = '51326'":
            True,
            "SELECT * FROM scenes WHERE mandragoreID = 40999 AND imageID = '52504824-10'":
            True,
            "SELECT * FROM scenes WHERE mandragoreID = 40999 AND imageID = '7842457-1'":
            False,
            "SELECT * FROM descriptors WHERE classID = 'abeille'":
            True,
            "SELECT * FROM descriptors WHERE classID = 'abeille' AND mandragoreID = 51125":
            True,
            "SELECT * FROM descriptors WHERE classID = 'oreilles' AND mandragoreID = 51125":
            False,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            self.prepare_data(tmpdir, TEST_FILES)
            with PersistMandlagore(os.path.join(tmpdir, 'mdlg-test.db')) as db:
                db.ensure_schema(True)

                mng = MandragoreDumpManager(tmpdir, db)
                # now try to import the files
                mng.load_basic_data()
                self.verify_db_content(db, queries)

    def test_bnf_dumps(self):
        queries = {
            "SELECT * FROM classes":
            True,
            "SELECT * FROM classes WHERE classID = 'biche'":
            True,
            "SELECT * FROM classes WHERE classID = 'abeille'":
            False,
            "SELECT * FROM images WHERE imageID = '7823277-1'":
            True,
            "SELECT * FROM images WHERE imageID = '52504824-151'":
            True,
            "SELECT * FROM scenes WHERE mandragoreID = '52957'":
            True,
            "SELECT * FROM scenes WHERE mandragoreID = 181563 AND imageID = '10308906-65'":
            True,
            "SELECT * FROM scenes WHERE mandragoreID = 40999 AND imageID = '10500687-147'":
            False,
            "SELECT * FROM descriptors WHERE classID = 'taureau'":
            True,
            "SELECT * FROM descriptors WHERE classID = 'taureau' AND mandragoreID = 10005":
            True,
            "SELECT * FROM descriptors WHERE classID = 'oreilles' AND mandragoreID = 10005":
            False,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            self.prepare_data(tmpdir, TEST_BNF_FILES)
            with PersistMandlagore(os.path.join(tmpdir, 'mdlg-test.db')) as db:
                db.ensure_schema(True)

                mng = MandragoreDumpManager(tmpdir, db)

                # now try to import the files
                mng.load_bnf_data()
                self.verify_db_content(db, queries)
