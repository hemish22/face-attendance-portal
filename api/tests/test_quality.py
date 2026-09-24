from types import SimpleNamespace

import numpy as np

from app.config import settings
from core.quality import check_enrollment_quality


def make_face(det_score=0.9, bbox=(100, 100, 300, 300), kps=None):
    if kps is None:
        # upright, symmetric keypoints -> yaw asymmetry ~0
        kps = np.array([[130, 150], [270, 150], [200, 200], [150, 260], [250, 260]], dtype=float)
    return SimpleNamespace(det_score=det_score, bbox=np.array(bbox, dtype=float), kps=kps)


def sharp_image(size=400):
    rng = np.random.default_rng(0)
    return rng.integers(0, 255, size=(size, size, 3), dtype=np.uint8)


def flat_image(size=400):
    return np.full((size, size, 3), 128, dtype=np.uint8)


def test_rejects_no_face():
    result = check_enrollment_quality([], sharp_image())
    assert not result.ok
    assert "no face" in result.reason.lower()


def test_rejects_multiple_faces():
    faces = [make_face(), make_face()]
    result = check_enrollment_quality(faces, sharp_image())
    assert not result.ok
    assert "one" in result.reason.lower() or "2" in result.reason


def test_rejects_tiny_face():
    faces = [make_face(bbox=(100, 100, 100 + settings.ENROLL_MIN_FACE_PX - 10, 300))]
    result = check_enrollment_quality(faces, sharp_image())
    assert not result.ok
    assert "small" in result.reason.lower()


def test_rejects_blurry_face():
    faces = [make_face()]
    result = check_enrollment_quality(faces, flat_image())
    assert not result.ok
    assert "blur" in result.reason.lower()


def test_accepts_good_face():
    faces = [make_face()]
    result = check_enrollment_quality(faces, sharp_image())
    assert result.ok
