
class Scene:
    pass

class Descriptor:
    pass
    #mandragoreID : int
    #X : float
    #Y : float
    #width : float
    #height : float

class IlluminationData:
    pass


class DigitalImageData:
    pass
    #width : int
    #height : int
    #ImageDB : str


class PageData:
    pass
    #id : str


class DocumentData:
    pass
    #id : str


class GalacticaURL:
    # https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11/398,195,2317,3945/full/0/native.jpg-1
    def __init__(self, url):
        self.url = url
        self.params = url.split("/")

    def is_valid(self) -> bool:
        return len(self.params) > 5 and \
               (self.params[2] == "gallica.bnf.fr" and self.params[3] == "iiif" and self.params[4] == "ark:")

    def document_id(self) -> str:
        return self.params[6][5:-1]

    def page_number(self) -> int:
        return int(self.params[7][1:])

    def size_px(self) -> {}:
        image_size = self.params[8]
        if image_size == 'full':
            return None
        location = [int(l) for l in self.params[8].split(",")]
        return {'x': location[0], 'y': location[1], 'width': location[2]-location[0]+1,
                              'height': location[3]-location[1]+1}

    def as_filename(self) -> str:
        return "_".join((self.document_id(), str(self.page_number())))

    def url_image_properties(self) -> str:
        parts = self.params[0:8]
        parts.append('info.json')
        return "/".join(parts)

def zone_in_zone_as_pct(outer_zone_px, inner_zone_px) -> dict:
    # each zone is describe as : x, y, width, height
    # absolute zone is in pixels (x, y is upper left corner, lower right is x+width, y+height
    # pct zone is a float where : x, y is middle of the inner zone (in pct) and widht, height in pct of outerzone

    w_pct = inner_zone_px['width'] / outer_zone_px['width']
    h_pct = inner_zone_px['height'] / outer_zone_px['height']
    x_middle_pct = (inner_zone_px['x'] + inner_zone_px['width'] / 2) / outer_zone_px['width']
    y_middle_pct = (inner_zone_px['y'] + inner_zone_px['height'] / 2) / outer_zone_px['height']

    return {'x':x_middle_pct, 'y':y_middle_pct, 'width':w_pct, 'height': h_pct}


def get_one_field_values(array_of_dict: list, fieldname: str) -> set:
    values = set()
    for r in array_of_dict:
        values.add(r[fieldname])
    return values

def reduce_fields(array_of_dict: list, fieldnames: list) -> list:
    values = []
    for r in array_of_dict:
        d = {d: r[d] for d in fieldnames}
    return values
