
import model


class FullImageFilePersistence:

    def __init__(self, rootDir):
        self.imageDir = rootDir


class MandragoreDumpLoader:

    def __init__(self, dumpZipFile):
        self.dumpZipFilename = dumpZipFile


class ViaLabelledImageLoader:

    def __init__(self, viaJsonFilename):
        self.via_json_filename = viaJsonFilename

    def load_labels(self) -> model.DocumentData:
        return model.DocumentData()


