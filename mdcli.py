
import click



#TODO to initialize the DB
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



@click.command()

def mdcli():
    raise NotImplementedError("under progress ...")


if __name__ == '__main__':
    mdcli()
