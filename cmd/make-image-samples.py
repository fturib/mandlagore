
#import sqlite3
#import persistence

from PIL import Image
import urllib.request

GALLICA_FORM = "https://gallica.bnf.fr/iiif/ark:/12148/btv1b{0}c/f{1}/full/pct:100/0/native.jpg"
DRE_FORM = "http://visualiseur.bnf.fr/ConsulterElementNum?O=IFN-{0}&E=JPEG&Deb={1}&Fin={1}&Param=E"
IMG_FILENAME = "{0}-{1}-{2}.jpg"
folder = "/Users/francois/Documents/Mandragore/sampleImages/"


fichier = "52504824-22"
docID = fichier.split("-")

urlGallica = str.format(GALLICA_FORM, docID[0], docID[1])
urlDRE = str.format(DRE_FORM, docID[0], docID[1])
source = "GALLICA"

imagename = str.format(IMG_FILENAME, docID[0], docID[1], source)
url = urlDRE if source == "DRE" else urlGallica

fullimagename = folder + imagename
print(str.format("image downloaded from : {0} saved in file {1}", url, fullimagename))
urllib.request.urlretrieve(url, fullimagename)

image = Image.open(fullimagename)
# image = image.resize((100, 100))
# summarize some details about the image
print(image.format)
print(image.mode)
print(image.size)
# show the image
image.show()
