import numpy as np
import pytest

from starfish.imagestack.imagestack import ImageStack
from starfish.spots._detector._base import SpotFinderAlgorithmBase
from starfish.spots._detector.blob import BlobDetector
from starfish.spots._detector.detect import detect_spots
from starfish.spots._detector.local_max_peak_finder import LocalMaxPeakFinder
from starfish.spots._detector.trackpy_local_max_peak_finder import TrackpyLocalMaxPeakFinder
from starfish.test.test_utils import (
    two_spot_informative_blank_coded_data_factory,
    two_spot_one_hot_coded_data_factory,
    two_spot_sparse_coded_data_factory,
)
from starfish.types import Axes, Features

_, ONE_HOT_IMAGESTACK, ONE_HOT_MAX_INTENSITY = two_spot_one_hot_coded_data_factory()
_, SPARSE_IMAGESTACK, SPARSE_MAX_INTENSITY = two_spot_sparse_coded_data_factory()
_, BLANK_IMAGESTACK, BLANK_MAX_INTENSITY = two_spot_informative_blank_coded_data_factory()


def simple_gaussian_spot_detector() -> BlobDetector:
    """create a basic gaussian spot detector"""
    return BlobDetector(min_sigma=1, max_sigma=4, num_sigma=5, threshold=0, measurement_type='max')


def simple_trackpy_local_max_spot_detector() -> TrackpyLocalMaxPeakFinder:
    """create a basic local max peak finder"""
    return TrackpyLocalMaxPeakFinder(
        spot_diameter=3,
        min_mass=0.01,
        max_size=10,
        separation=2,
    )


def simple_local_max_spot_detector() -> LocalMaxPeakFinder:
    return LocalMaxPeakFinder(
        min_distance=6,
        stringency=0,
        min_obj_area=0,
        max_obj_area=np.inf,
        threshold=0
    )


# initialize spot detectors
gaussian_spot_detector = simple_gaussian_spot_detector()
trackpy_local_max_spot_detector = simple_trackpy_local_max_spot_detector()
local_max_spot_detector = simple_local_max_spot_detector()

# test parameterization
test_parameters = (
    'data_stack, spot_detector, radius_is_gyration, max_intensity',
    [
        (ONE_HOT_IMAGESTACK, gaussian_spot_detector, False, ONE_HOT_MAX_INTENSITY),
        (ONE_HOT_IMAGESTACK, trackpy_local_max_spot_detector, True, ONE_HOT_MAX_INTENSITY),
        (ONE_HOT_IMAGESTACK, local_max_spot_detector, False, ONE_HOT_MAX_INTENSITY),
        (SPARSE_IMAGESTACK, gaussian_spot_detector, False, SPARSE_MAX_INTENSITY),
        (SPARSE_IMAGESTACK, trackpy_local_max_spot_detector, True, SPARSE_MAX_INTENSITY),
        (SPARSE_IMAGESTACK, local_max_spot_detector, False, SPARSE_MAX_INTENSITY),
        (BLANK_IMAGESTACK, gaussian_spot_detector, False, BLANK_MAX_INTENSITY),
        (BLANK_IMAGESTACK, trackpy_local_max_spot_detector, True, BLANK_MAX_INTENSITY),
        (BLANK_IMAGESTACK, local_max_spot_detector, False, BLANK_MAX_INTENSITY),
    ]
)


@pytest.mark.parametrize(*test_parameters)
def test_spot_detection_with_reference_image(
        data_stack: ImageStack,
        spot_detector: SpotFinderAlgorithmBase,
        radius_is_gyration: bool,
        max_intensity: float,
):
    """This testing method uses a reference image to identify spot locations."""
    reference_image_mp = data_stack.max_proj(Axes.CH, Axes.ROUND)
    reference_image_mp_numpy = reference_image_mp._squeezed_numpy(Axes.CH, Axes.ROUND)

    intensity_table = detect_spots(data_stack=data_stack,
                                   spot_finding_method=spot_detector.image_to_spots,
                                   reference_image=reference_image_mp_numpy,
                                   measurement_function=np.max,
                                   radius_is_gyration=radius_is_gyration)
    assert intensity_table.sizes[Features.AXIS] == 2, "wrong number of spots detected"
    expected = [max_intensity * 2, max_intensity * 2]
    assert np.allclose(intensity_table.sum((Axes.ROUND, Axes.CH)).values, expected), \
        "wrong spot intensities detected"


@pytest.mark.parametrize(*test_parameters)
def test_spot_detection_with_reference_image_from_max_projection(
        data_stack: ImageStack,
        spot_detector: SpotFinderAlgorithmBase,
        radius_is_gyration: bool,
        max_intensity: float,
):
    """This testing method builds a reference image to identify spot locations."""
    intensity_table = detect_spots(data_stack=data_stack,
                                   spot_finding_method=spot_detector.image_to_spots,
                                   reference_image_from_max_projection=True,
                                   measurement_function=np.max,
                                   radius_is_gyration=radius_is_gyration)
    assert intensity_table.sizes[Features.AXIS] == 2, "wrong number of spots detected"
    expected = [max_intensity * 2, max_intensity * 2]
    assert np.allclose(intensity_table.sum((Axes.ROUND, Axes.CH)).values, expected), \
        "wrong spot intensities detected"


@pytest.mark.parametrize(*test_parameters)
def test_spot_finding_no_reference_image(
        data_stack: ImageStack,
        spot_detector: SpotFinderAlgorithmBase,
        radius_is_gyration: bool,
        max_intensity: float,
):
    """
    This testing method does not provide a reference image, and should therefore check for spots
    in each (round, ch) combination in sequence. With the given input, it should detect 4 spots.
    """
    intensity_table = detect_spots(data_stack=data_stack,
                                   spot_finding_method=spot_detector.image_to_spots,
                                   measurement_function=np.max,
                                   radius_is_gyration=radius_is_gyration)
    assert intensity_table.sizes[Features.AXIS] == 4, "wrong number of spots detected"
    expected = [max_intensity] * 4
    assert np.allclose(intensity_table.sum((Axes.ROUND, Axes.CH)).values, expected), \
        "wrong spot intensities detected"
