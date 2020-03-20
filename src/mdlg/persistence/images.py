import cv2.cv2 as cv2
from typing import List, Tuple, Dict, Iterable
from PIL import Image
import numpy as np
import os
from dh_segment.post_processing import boxes_detection, binarization
from dh_segment.utils.evaluation import Metrics


def get_image_shape_without_loading(filename) -> Tuple[int, int]:
    image = Image.open(filename)
    h, w = image.size
    image.close()
    return (w, h)


def xywh_to_points(x: int, y: int, w: int, h: int) -> ():
    return ((x, y), (x + w, y), (x + w, y + h), (x, y + h))


def lxywh_to_points(xywh: ()) -> ():
    return xywh_to_points(*xywh)


def points_to_xywh(points: ()) -> ():
    x, y, w, h = points[0][0], points[0][1], points[1][0] - points[0][0], points[2][1] - points[1][1]
    if w < 0:
        x, w = x + w, -w
    if h < 0:
        y, h = y + h, -h
    return (x, y, w, h)


class ImageZones:
    def __init__(self, name: str, w: int, h: int, zones: ()):
        self.name = name
        self.w = w
        self.h = h

        # content is the name of the file that represent the image (usually jpg). the size is most likely not at scale.
        #                     onDiskW, onDiskH = get_image_shape_without_loading(os.path.join(images_dir, gal.as_filename()))=
        # zone is a sequence of ZONES = quadruplets (x, y, w, h) related to the full image : (0,0,refwidth,refheight)
        self.zones = list(zones)

    # @classmethod
    # def fromPageAndBoxes(cls, otherPage, boxes: ()):
    #     regions = []
    #     for box in boxes:
    #         cv2.polylines(orig_img, [box[:, None, :]], True, (0, 0, 255), thickness=15)
    #         regions.append(PAGE.GraphicRegion(coords=PAGE.Point.cv2_to_point_list(pred_box[:, None, :])))
    #     return ImageZones(otherPage._name, otherPage._refwidth, otherPage._refheight, otherPage._filename, regions)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def rescale(self, fw: int, fh: int):
        scalew, scaleh = fw / self.w, fh / self.h
        szones = ((int(x * scalew), int(y * scaleh), int(w * scalew), int(h * scaleh)) for (x, y, w, h) in self.zones)
        return ImageZones(self.name, fw, fh, szones)

    def eval(self, predicted_zones: ()):
        def intersection_over_union(cnt1, cnt2):
            mask1 = np.zeros([self.w, self.h], np.uint8)
            mask1 = cv2.fillConvexPoly(mask1, cnt1.astype(np.int32), 1).astype(np.int8)
            mask2 = np.zeros([self.w, self.h], np.uint8)
            mask2 = cv2.fillConvexPoly(mask2, cnt2.astype(np.int32), 1).astype(np.int8)

            return np.sum(mask1 & mask2) / np.sum(mask1 | mask2)

        def compute_metric_boxes(predicted_boxes: np.array, label_boxes: np.array, threshold: float = 0.8):
            # Todo test this fn
            metric = Metrics()
            if label_boxes is None:
                if predicted_boxes is None:
                    metric.true_negatives += 1
                    metric.total_elements += 1
                else:
                    metric.false_negatives += len(predicted_boxes)

            else:
                for pb in predicted_boxes:
                    best_iou = 0
                    for lb in label_boxes:
                        iou = intersection_over_union(pb[:, None, :], lb[:, None, :])
                        if iou > best_iou:
                            best_iou = iou

                    if best_iou > threshold:
                        metric.true_positives += 1
                        metric.IOU_list.append(best_iou)
                    elif best_iou < 0.1:
                        metric.false_negatives += 1
                    else:
                        metric.false_positives += 1
                        metric.IOU_list.append(best_iou)

            metric.total_elements += len(label_boxes)
            return metric

        return compute_metric_boxes(np.array(list(map(lxywh_to_points, predicted_zones)), np.int8), np.array(list(map(lxywh_to_points, self.zones)), np.int8))

    def find_boxes(self, prediction_outputs: dict):
        probs = prediction_outputs['probs'][0]
        h, w = prediction_outputs['original_shape']
        probs = probs[:, :, 1]  # Take only class '1' (class 0 is the background, class 1 is the page)
        probs = probs / np.max(probs)  # Normalize to be in [0, 1]

        page_bin = self.ornaments_post_processing_fn(probs)
        # orig_img = imread(self._page.contentFilename(), mode='RGB')
        # target_shape = (orig_img.shape[1], orig_img.shape[0])
        bin_upscaled = cv2.resize(np.uint8(page_bin), (w, h), interpolation=cv2.INTER_NEAREST)
        # if debug:
        #    imsave(os.path.join(output_dir, '{}_bin.png'.format(basename)), bin_upscaled)
        pred_box = boxes_detection.find_boxes(np.uint8(bin_upscaled), mode='min_rectangle', min_area=0.005, n_max_boxes=10)
        # translate the boxes into zones or have an handy util to compute it
        # pred_box is a list of bozes defined by 4-points
        return map(points_to_xywh, pred_box)

    def ornaments_post_processing_fn(self, probs: np.ndarray, threshold: float = 0.5, ksize_open: tuple = (5, 5), ksize_close: tuple = (7, 7)) -> np.ndarray:
        if threshold < 0:  # Otsu thresholding
            probs_ch = np.uint8(probs * 255)
            blur = cv2.GaussianBlur(probs_ch, (5, 5), 0)
            thresh_val, bin_img = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            mask = bin_img / 255
        else:
            mask = probs > threshold
            # TODO : adaptive kernel (not hard-coded)
        mask = cv2.morphologyEx((mask.astype(np.uint8) * 255), cv2.MORPH_OPEN, kernel=np.ones(ksize_open))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel=np.ones(ksize_close))

        result = mask / 255
        return result

    def page_make_binary_mask(self, probs: np.ndarray, threshold: float = -1) -> np.ndarray:
        """
        Computes the binary mask of the detected Page from the probabilities outputed by network
        :param probs: array with values in range [0, 1]
        :param threshold: threshold between [0 and 1], if negative Otsu's adaptive threshold will be used
        :return: binary mask
        """

        mask = binarization.thresholding(probs, threshold)
        mask = binarization.cleaning_binary(mask, kernel_size=5)
        return mask

    def create_mask(self) -> np.array:
        return np.zeros([self.w, self.h], np.uint8)

    def draw_zones(self, img: np.array, zones: (), contours_only: bool = False) -> np.array:
        # if the image has no annotation, writing a black mask:
        for (x, y, w, h) in zones:
            contours = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]).reshape((-1, 1, 2))
            img = cv2.polylines(img, [contours], True, 255, thickness=15) if contours_only \
                else cv2.fillPoly(img, [contours], 255)

        return img
