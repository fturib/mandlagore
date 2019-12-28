
import json
import os

JSON_DATA_PATH = "/Users/francois/Documents/Mandragore/DetourageImages"


files = []
pages = {}
totalFiles = 0
totalPages = 0
totalEnluminures = 0
totalDescriptors = 0
# r=root, d=directories, f = files
for r, d, f in os.walk(JSON_DATA_PATH):
    for file in f:
        if '.json' in file:
            files.append(os.path.join(r, file))

for f in files:
    with open(f, "r") as fp:
        data = json.load(fp)

    totalFiles+=1
    # print("filename : ", f)
    # print(data)

    for k, v in data.items():
        totalEnluminures+=1
        totalDescriptors+=len(v["regions"])

        params = v["filename"].split("/")
        pageName = params[6]
        pageNumber = params[7]
        location = params[8]

        pageID = pageName[5:-1]+"-"+pageNumber[1:]



        pages[pageID] = location

        print("page %s - key URL galactica : %s" % (pageID, k))

        # filename (eg https://gallica.bnf.fr/iiif/ark:/12148/btv1b8419219x/f338/158,816,2411,1797/full/0/native.jpg)
            # split on / - take [6] -> extract noticeID, take[7] -> extract f+page / take [8] -> extract coord
        # size
        # regions - array
            # shape_attributes - dict
                # name
                # x, y, width, height
            # region_attributes - dict
                # Descripteur
                # Type
        # file_attribute - dict
                # MandragoreId



        # TODO
        # -> add/replace entry MandragoreID (Notice) - to fichier / page - coordinates
        # -> add/replace entry LabelDescriptor - MandragoreID, Region, Description, Type


totalPages = len(pages)
print("files : %d" % totalFiles)
print("pages : %d" % totalPages)
print("enluminures : %d" % totalEnluminures)
print("descriptions : %d" % totalDescriptors)
