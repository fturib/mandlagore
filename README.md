# mandlagore

Expect help to label Mandragore db using Deep Learning on the illuminations of digitalized images of manuscripts
main DB of images are Gallica and DRE.

Explanation of data available for Mandragore is available [here, on the BNF website](http://api.bnf.fr/dumps-mandragore)
We needs to download images from the BNF's db Gallica. Description of the API is available here: [IIIF's API for fetching images from Gallica](http://api.bnf.fr/api-iiif-de-recuperation-des-images-de-gallica)

## Status

**Under progress AND NOT STABLE.**

As of now, the following pieces are implemented, with (too few) UT.

* 1- build DB schema
* 2- fill DB from the standard dump of Mandragore - ability to refill (clean or add)
* 3- load in DB the label manually defined using VIA - ability to overload

a CLI is available to trigger those commands

## Installation

the package has to be installed either for enhancing the development, either to use it from within another program.

NOTE: I still need to test if the installation happen from github.

```bash
# create your conda environment
conda create -n aname python=3.6
conda activate aname
python setup develop <root-folder-of-code>
```

### Runnint the unit tests

```bash
# cd <root-folder-of-code-mdlg>
python -m unittest tests/test_*.py -v
```

## CLI

### Help on the CLI

python3 mdcli.py --help

a "MDLG_DATA" root folder is need to locate the DB and the data for import, download or process
that root folder can be provided either as an option on the command line, or as a environment variable: $MDLG_DATA

### Environment and reset a new DB

```bash
cd
mkdir mdlg-data
export MDLG-DATA=~/mdlg-data
```

```bash
python3 mdcli.py --root=~/mdlg-data reset
```

if the env variable named $MDLG_DATA is defined:

```bash
python3 mdcli.py reset
```

there program prompts for a confirmation. To avoid this step, add the option '--yes' on the command line:

```bash
python3 mdcli.py reset --yes
```

### load dumps from Mandragore in DB

Documentation on this data is available here on [Mandragore : jeu d'images annotées sur le thème de la zoologie](http://api.bnf.fr/mandragore-jeu-dimages-annotees-sur-le-theme-de-la-zoologie)

You need to download the [zip file provided by Mandragore project](ftp://ftp.bnf.fr/api/jeux_docs_num/Images/Mandragore/Zoologie/metadata/metadata.zip), and unzip it in the `import/mandragore-dumps` folder

```bash
cd ~/tmp
wget ftp://ftp.bnf.fr/api/jeux_docs_num/Images/Mandragore/Zoologie/metadata/metadata.zip
unzip metadata.zip
cp metadata/* $MDLG_DATA/import/mandragore-dumps
rm -rf metadata
rm metadata.zip
cd $MDLG_DATA/import/mandragore-dumps
```

then run the cli to import those files in DB:

```bash
python3 mdcli.py mandragore
```

### load via annotations of some illumination

Mandragore Team started to label documents.
They use the [VIA annotation tool, v2, available here](http://www.robots.ox.ac.uk/~vgg/software/via/)

the json files, result of this labelisation are presented on this page of the bnf website: [Échantillon segmenté d'enluminures de Mandragore](http://api.bnf.fr/mandragore-echantillon-segmente-2019)

you will need to download the raw annotations in json format provided on this page:

```bash
cd ~/tmp
wget ftp://ftp.bnf.fr/api/jeux_docs_num/Mandragore/Segmentation2019.zip
unzip Segmentation2019.zip
cp Segmentation2019/RawVIAData/VIA* $MDLG_DATA/import/via-labels
rm -rf Segmentation2019
rm Segmentation2019.zip
cd $MDLG_DATA/import/via-labels
```

then run the cli to import those label files in DB:

```bash
python3 mdcli.py labels
```

### download image content and image sizes from Galactica

the API of Galactica, for collecting images on demand, is available on (IIIF's API for fetching images from Gallica)[http://api.bnf.fr/api-iiif-de-recuperation-des-images-de-gallica]
Mandlagore keep metadata of the images in the BD, and their content in local files available at `${MDLG-DATA}/images/galactica`
to download missing content and missing metadata (the size of images), cun cli:

```bash
python3 mdcli.py galactica
```

This command has several option to filter and limit the scope of images:

* `-limit <max-images>` to limit total number of images to process
* `-i <image-id>` to filter the images, * pattern is available, several id is possible if separated by comma
* `-i <fieldname==value>` to filter on another metadata of images (documentUDL, width or height)
* `-i localized` to filter on images that have already a size defined in DB
* `-s <mandragore-id,image-id>` to filter the images on the connected scenes, * pattern is available, several id is possible if separated by comma
* `-s <fieldname==value>` to filter on another metadata of scenes (mandragoreID, imageID, x, h, widht, height)
* `-s localized` to filter on images that are connected to a scene that have already a position/size defined in DB
* `-d <mandragore-id,class-id>` to filter the images on the connected scenes that includes a descriptor, * pattern is available, several id is possible if separated by comma
* `-d <fieldname==value>` to filter on another metadata of descriptors (mandragoreID, classID, x, h, widht, height)
* `-d localized` to filter on images that are connected to a scene that have a descriptor that has already a position/size defined in DB
* `--dryrun` to simulate the operations: only the list of actions to operate (download content, download size) is printed. No actions taken
* `--faked` to operate with fake download : content and size are generated in place of download - for tests purposes only

NOTE: check the help of this command with : `python3 mdcli.py galactica --help`