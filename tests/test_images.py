import unittest
import mdlg.persistence.images as images
import os
import tempfile
from imageio import imread, imsave
import numpy as np
from dh_segment.utils.evaluation import Metrics


class TestImageZones(unittest.TestCase):
    def test_rescale(self):
        TESTS = {
            'simple': ((200, 200, ((10, 10, 50, 50), )), (20, 20, ((1, 1, 5, 5), ))),
            'several': ((500, 300, ((50, 50, 100, 100), (200, 50, 5, 50))), (100, 30, ((10, 5, 20, 10), (40, 5, 1, 5))))
        }
        for k, v in TESTS.items():
            (w, h, zones), (sw, sh, szones) = v
            iz = images.ImageZones(k, w, h, zones)
            izs = iz.rescale(sw, sh)
            self.assertEqual(izs.w, sw)
            self.assertEqual(izs.h, sh)
            self.assertEqual(izs.zones, list(szones))

    def test_eval(self):
        TESTS = {
            'simple': {
                'iz': (200, 200, ((10, 10, 50, 50), )),
                'predicted': ((10, 10, 50, 50), ),
                'metrics': (1, 1)
            },
            'several': {
                'iz': (100, 100, ((0, 0, 10, 10), (100, 100, 10, 10))),
                'predicted': ((0, 0, 10, 10), ),
                'metrics': (2, 1),
            },
            'all-match': {
                'iz': (100, 100, ((0, 0, 10, 10), (50, 50, 10, 10))),
                'predicted': ((0, 0, 10, 10), (50, 50, 10, 10)),
                'metrics': (2, 2),
            }
        }
        for k, v in TESTS.items():
            w, h, zones = v['iz']
            predicted = v['predicted']

            iz = images.ImageZones(k, w, h, zones)
            m = iz.eval(predicted)
            self.assertEqual(m.total_elements, v['metrics'][0])
            self.assertEqual(m.true_positives, v['metrics'][1])

    def test_find_boxes(self):
        TESTS = {
            'simple': (200, 200, ((10, 10, 50, 50), )),
            'several': (30, 30, ((0, 0, 10, 10), (15, 15, 10, 10))),
        }
        for k, v in TESTS.items():
            w, h, zones = v
            iz = images.ImageZones(k, w, h, zones)
            mask = iz.create_mask()
            img = iz.draw_zones(mask, zones)
            img = img[:, :, None]
            img = np.append(img, img, axis=2)
            # expand the image on background and class1

            predictions = {'probs': [img], 'original_shape': (w, h)}

            pred_zones = iz.find_boxes(predictions)

            self.assertEqual(set(pred_zones), set(zones))


class TestImageFunctions(unittest.TestCase):
    def test_point_conversions(self):
        TESTS = {'simple': {'xywh': (0, 5, 10, 20), 'points': ((0, 5), (10, 5), (10, 25), (0, 25))}}
        for k, v in TESTS.items():
            cpoints = images.xywh_to_points(*v['xywh'])
            cxywh = images.points_to_xywh(v['points'])

            self.assertEqual(cpoints, v['points'])
            self.assertEqual(cxywh, v['xywh'])

    def test_get_shape(self):
        TESTS = {'simple': (100, 100, ((10, 10, 50, 50), )), 'large': (1200, 475, ((0, 0, 10, 10), (100, 100, 10, 10)))}
        with tempfile.TemporaryDirectory() as tmpdir:
            for k, v in TESTS.items():
                w, h, zones = v
                iz = images.ImageZones(k, w, h, zones)
                img = iz.draw_zones(iz.create_mask(), iz.zones, False)
                filename = os.path.join(tmpdir, k + '.png')
                imsave(filename, img.astype(np.uint8))

                iw, ih = images.get_image_shape_without_loading(filename)

                self.assertEqual(iw, w)
                self.assertEqual(ih, h)
