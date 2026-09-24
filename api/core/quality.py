"""Enrollment quality gate. Pure Python — no FastAPI or DB imports."""

from dataclasses import dataclass

import cv2
import numpy as np

from app.config import settings


@dataclass
class QualityResult:
    ok: bool
    reason: str | None = None


def laplacian_variance(gray_crop: np.ndarray) -> float:
    return float(cv2.Laplacian(gray_crop, cv2.CV_64F).var())


def yaw_asymmetry(kps: np.ndarray) -> float:
    """kps: 5x2 array [left_eye, right_eye, nose, mouth_l, mouth_r]."""
    left_eye_x, right_eye_x, nose_x = kps[0][0], kps[1][0], kps[2][0]
    eye_span = right_eye_x - left_eye_x
    if eye_span == 0:
        return 1.0
    return abs((nose_x - left_eye_x) - (right_eye_x - nose_x)) / eye_span


def check_enrollment_quality(faces: list, image: np.ndarray) -> QualityResult:
    """faces: list of insightface Face objects detected in one enrollment photo."""
    if len(faces) == 0:
        return QualityResult(False, "No face detected")
    if len(faces) > 1:
        return QualityResult(False, f"{len(faces)} faces detected, expected exactly one")

    face = faces[0]

    if face.det_score < settings.ENROLL_MIN_DET:
        return QualityResult(False, f"Detection confidence too low ({face.det_score:.2f})")

    x1, y1, x2, y2 = face.bbox
    width = x2 - x1
    if width < settings.ENROLL_MIN_FACE_PX:
        return QualityResult(False, f"Face too small ({width:.0f}px wide)")

    x1i, y1i, x2i, y2i = int(max(x1, 0)), int(max(y1, 0)), int(x2), int(y2)
    crop = image[y1i:y2i, x1i:x2i]
    if crop.size == 0:
        return QualityResult(False, "Face crop out of bounds")
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blur = laplacian_variance(gray)
    if blur < settings.ENROLL_MIN_BLUR:
        return QualityResult(False, f"Photo too blurry (sharpness {blur:.0f})")

    asym = yaw_asymmetry(face.kps)
    if asym > settings.ENROLL_MAX_YAW_ASYM:
        return QualityResult(False, f"Face too angled (asymmetry {asym:.2f})")

    return QualityResult(True)


def is_duplicate(embedding: np.ndarray, other_member_ref_embeddings: np.ndarray, threshold: float = 0.6) -> bool:
    if other_member_ref_embeddings.size == 0:
        return False
    scores = other_member_ref_embeddings @ embedding
    return bool(scores.max() >= threshold)
