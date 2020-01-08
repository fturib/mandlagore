import click
import os
from mdlg.persistence.db import PersistMandlagore
from mdlg.persistence.remoteHttp import GalacticaSession
from mdlg.services.mandragore_dump_manager import MandragoreDumpManager
from mdlg.services.via_label_manager import ViaLabelManager
from mdlg.services.image_manager import ImagesManager

# TODO to initialize the DB
# 1- we consider the schema is ready
# 2- load CSV files into SQLite and use an SQL to insert into the corresponding tables
# TODO - choose the option to update(add) or replace

# What we want to be able to do
#
# 1- build DB schema
# 2- fill DB from the standard dump of Mandragore - ability to refill (clean or add)
# 3- load in DB the label manually defined using VIA - ability to overload
# 4- generate training sets for illumination location detection - <parameters to define>
# 5- run training of the ML for illumination detection and estimate accuracy - keep track
# 6- compute prediction of illumination detection for all pages tied to Mandlagore - save results in DB (and compare with former predictions)
# 7- generate training sets for class detection - <parameters to define, maybe root of files folders>
# 8- run training of the ML for class detection and estimate accuracy - keep track
# 9- compute both prediction on a random page of manuscript

# mdcli --rootpath
#  arguments :
#   reset (clear all the data folder, w/o backup)
#   backup  <where> - backup the full DATA folder into a data-xx-date.zip to be saved in the backup folder
#   restore <from-where> <what-version>
#   download <from-where> (download dump files and label files - that are missing)
#   mandragore (update dumps with latests and update the DB)
#   labels (integrate labelization into the DB)
#   galactica (download missing image files from galactica, along with missing image sizes)
#   dhsegment (generate the training set for dh-segment, and run the training for dh-segment - return accuracy)
#   predict-scene <document-id, page> (download the image, get a prediction for dhsegment, extract the scene, and show result)
#   classify (generate the training-set for class detection and run the training for class detection - return accuracy)
#   predict <document-id, page> (download the image, and then compute a prediction for class - and the image produced)

# -/ (default to position of current file / DATA
# ---  mdlg.db
# ---  images
# -------/ galactica (downloaded for galactica)
# -------/ generated
# ------------/dhsegment
# ----------------/ training
# ----------------/ predict
# ------------/classify
# ----------------/ training
# ----------------/ predict
# ---  import
# -------/ mandragore-dump
# -------/ csv-labels


class MdlgEnv(object):
    DIR_LOCATION = {
        'images': 'images',
        'galactica': 'images/galactica',
        'dre': 'images/dre',
        'dhsegment_train': 'images/generated/dhsegment/train',
        'dhsegment_predict': 'images/generated/dhsegment/predict',
        'classify_train': 'images/generated/classify/train',
        'classify_predict': 'images/generated/classify/predict',
        'import_dumps': 'import/mandragore-dumps',
        'import_labels': 'import/via-labels'
    }
    DB_FILENAME = 'mdlg.db'

    def __init__(self, rootdir:str):
        super().__init__()
        self._rootdir = rootdir
        for k in MdlgEnv.DIR_LOCATION:
            self._ensure_and_check_dir(k)

    def db_filename(self) -> str:
        return os.path.join(self._rootdir, MdlgEnv.DB_FILENAME)

    def _ensure_and_check_dir(self, key_name) -> str:
        dname = os.path.join(self._rootdir, MdlgEnv.DIR_LOCATION[key_name])
        if not os.path.exists(dname):
            os.makedirs(dname, exist_ok=True)
        if not os.path.isdir(dname):
            raise Exception("the target directory for {} is {} and is already existing as a file".format(key_name, dname))
        return dname

    def dump_data_dirname(self) -> str:
        return self._ensure_and_check_dir('import_dumps')

    def via_annotation_dirname(self) -> str:
        return self._ensure_and_check_dir('import_labels')

    def source_images_dirname(self) -> str:
        return self._ensure_and_check_dir('images')

    def source_images_galactica_dirname(self) -> str:
        return self._ensure_and_check_dir('galactica')

    def __repr__(self):
        return '<MdlgEnv %r>' % self._rootdir


pass_env = click.make_pass_decorator(MdlgEnv)

# envvar 'MDLG_DATA' is pointing the dir where we can find the DB and folders for saving images, data for trainingm prediction etc ...


@click.group()
@click.version_option('0.01')
@click.option("--root",
              type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True, readable=True, resolve_path=True, allow_dash=False),
              envvar='MDLG_DATA')
@click.pass_context
def mdcli(ctx, root):
    ctx.obj = MdlgEnv(root)


@mdcli.command()
@click.confirmation_option(prompt='Are you sure you want to reset all data, including dropping the db?')
@pass_env
def reset(mdlgenv: MdlgEnv):
    # ensure the DB file is wiped-out
    pathdb = mdlgenv.db_filename()
    if os.path.exists(pathdb):
        if not os.path.isfile(pathdb):
            raise Exception("the root dir provided contains already a dir named {} - it should be a simple file".format(pathdb))
        os.remove(pathdb)

    with PersistMandlagore(pathdb) as db:
        version = db.ensure_schema(rebuilt=True)
        click.echo("Mdlg DB rebuilt on file : {} - version {}".format(mdlgenv.db_filename(), version))


@mdcli.command()
def backup():
    click.echo("Not yet implemented")


@mdcli.command()
def restore():
    click.echo("Not yet implemented")


@mdcli.command()
def download():
    click.echo("Not yet implemented")


@mdcli.command()
@pass_env
def mandragore(mdlgenv: MdlgEnv):
    # load last downloaded dumps in the DB
    pathdb = mdlgenv.db_filename()
    with PersistMandlagore(pathdb) as db:
        dname = mdlgenv.dump_data_dirname()
        mng = MandragoreDumpManager(dname, db)
        report = mng.load_bnf_data()
        click.echo("Mdlg Mandragore dump files loaded into the DB")
        for file, report, warnings in report:
            click.echo("%s : %s" % (file, report))
            if len(warnings) > 0:
                click.echo("%d warning reported, 10 first warnings below:" % len(warnings))
                for w in warnings[:10]:
                    click.echo(" -- W -- %s" % w)


@mdcli.command()
@pass_env
def labels(mdlgenv: MdlgEnv):
    # load labels frol all the VIA annotation files available in the import folder
    pathdb = mdlgenv.db_filename()
    with PersistMandlagore(pathdb) as db, GalacticaSession() as gal:
        dname = mdlgenv.via_annotation_dirname()
        vlm = ViaLabelManager(dname, db, gal)
        report = vlm.import_labels()

        click.echo("Mdlg labels (VIA annotations) imported into the DB")
        for file, warnings, report in report:
            click.echo("%s : %s" % (file, report))
            if len(warnings) > 0:
                click.echo("%d warning reported at preparation, 10 first warnings below:" % len(warnings))
                for w in warnings[:10]:
                    click.echo(" -- W -- %s" % w)

def build_filter_from_option(param:str, value:str) -> list:
    # value can be one : 'localized', <string-with-no-*>, <string-with-star>, , separated of strings with no *
    # <fielname>==<value> or , separated values
    fn = 'ID'
    v = value
    if v == 'localized':
        fn = 'localized'
        v = None
    else:
        parts = v.split('==')
        if len(parts)>1:
            fn = parts[0]
            v = parts[1]
        lval = v.split(',')
        if len(lval)>1:
            fn +=':list'
            v = lval
        else:
            if v.find('*') >= 0:
                fn += ':like'
                v = v.replace("*", "%")
    
    return [param, fn, v]



@mdcli.command()
@pass_env
@click.option('-i', '--images', multiple=True, help="filtering on images\nformat is [field==](value|patttern|(val,)*)")
@click.option('-s', '--scenes', multiple=True, help="filtering on scenes, with same format as above")
@click.option('-d', '--descriptors', multiple=True, help="filtering on descriptors, with same format as above")
@click.option('-l', '--limit', type=int, help="limit quantity images to process")
@click.option('--dryrun', is_flag=True, help="download operations are avoided, only actions are printed")
@click.option('--faked', is_flag=True, help="download is simulated")
def galactica(mdlgenv: MdlgEnv, images, scenes, descriptors, limit, dryrun, faked):
    # complete download informations from Galactica : images and size of images
    # we should have filters:
    # -all to download everything
    # -scenes to complete only images involved in scenes that are located (have a defined position in the image)
    # -size for size only
    pathdb = mdlgenv.db_filename()
    filter = [build_filter_from_option('images', f) for f in images]
    filter += [build_filter_from_option('scenes', f) for f in scenes]
    filter += [build_filter_from_option('descriptors', f) for f in descriptors]
    with PersistMandlagore(pathdb) as db, GalacticaSession() as gal:
        imgr = ImagesManager(mdlgenv.source_images_galactica_dirname(), db, gal)
        imgr.ensure_content_images(filter, limit, dryrun, faked)

@mdcli.command()
def dhsegment():
    click.echo("Not yet implemented")


@mdcli.command()
def predict():
    click.echo("Not yet implemented")


@mdcli.command()
def classify():
    click.echo("Not yet implemented")


if __name__ == '__main__':
    mdcli()
