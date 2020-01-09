ZONE_FULL = (0, 0, None, None)
SIZE_FULL = (None, None)
ZONE_KEYS = ('x', 'y', 'width', 'height')
SIZE_KEYS = ('width', 'height')


class GalacticaURL:
    # https://gallica.bnf.fr/iiif/ark:/12148/btv1b8470209d/f11/398,195,2317,3945/full/0/native.jpg-1
    def __init__(self, parts):
        self.params = parts

    @classmethod
    def from_url(cls, url):
        parts = url.split("/")
        parts += ([''] * (12 - len(parts)))
        return cls(parts)

    def is_valid(self) -> bool:
        return len(self.params) > 5 and \
            (self.params[2] == "gallica.bnf.fr" and self.params[3] == "iiif" and self.params[4] == "ark:")

    def document_id(self) -> str:
        return self.params[6][5:-1]

    def page_number(self) -> int:
        return int(self.params[7][1:])

    def zone(self) -> ():
        return ZONE_FULL if self.params[8] is None or self.params[8] == 'full' else dict(zip(ZONE_KEYS, map(int, self.params[8].split(","))))

    def size(self) -> ():
        return SIZE_FULL if self.params[9] is None or self.params[9] == 'full' else dict(zip(SIZE_KEYS, map(int, self.params[9].split(","))))

    def rotation(self) -> int:
        return int(self.params[10]) | 0

    def quality(self) -> str:
        return self.params[11].split(".")[0]

    def file_format(self) -> str:
        end = self.params[11].split(".")
        return end[1] if len(end) > 1 else ""

    def as_filename(self) -> str:
        # TDO - review if we want to encode subset/rotation/zoom in the file
        return f"IMG-{self.document_id()}_P-{self.page_number()}.{self.file_format()}"

    def as_url(self) -> str:
        return "/".join(self.params)

    def url_image_properties(self):
        return GalacticaURL(self.params[0:8] + ['info.json'])

    def set_zone(self, zone=ZONE_FULL):
        szone = "full" if zone is None or zone == "full" or zone == ZONE_FULL else ",".join(map(str, zone))
        parts = self.params[0:8] + [szone] + self.params[9:]
        return GalacticaURL(parts)

    def set_size(self, final_size=SIZE_FULL):
        ssize = "pct:%d" % int(final_size) if isinstance(final_size, int) else \
            "full" if final_size is None or final_size == SIZE_FULL else ",".join(map(str, final_size))
        parts = self.params[0:9] + [ssize] + self.params[10:]
        return GalacticaURL(parts)

    def set_rotation(self, rotation=0):
        parts = self.params[0:10] + [str(rotation)] + self.params[11:]
        return GalacticaURL(parts)

    def set_quality(self, quality="native"):
        parts = self.params[0:11] + ["%s.%s" % (quality, self.file_format())]
        return GalacticaURL(parts)

    def set_file_format(self, file_format="jpg"):
        parts = self.params[0:11] + ["%s.%s" % (self.quality(), file_format)]
        return GalacticaURL(parts)


def zone_in_zone_as_pct(outer_zone_px, inner_zone_px) -> dict:
    # each zone is describe as : x, y, width, height
    # absolute zone is in pixels (x, y is upper left corner, lower right is x+width, y+height
    # pct zone is a float where : x, y is middle of the inner zone (in pct) and widht, height in pct of outerzone

    w_pct = inner_zone_px['width'] / outer_zone_px['width']
    h_pct = inner_zone_px['height'] / outer_zone_px['height']
    x_middle_pct = (inner_zone_px['x'] + inner_zone_px['width'] / 2) / outer_zone_px['width']
    y_middle_pct = (inner_zone_px['y'] + inner_zone_px['height'] / 2) / outer_zone_px['height']

    return {'x': x_middle_pct, 'y': y_middle_pct, 'width': w_pct, 'height': h_pct}


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
