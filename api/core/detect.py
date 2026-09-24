"""Full-image + tiled face detection, merged with NMS. Pure Python — no FastAPI or DB imports."""

from dataclasses import dataclass

import numpy as np

from app.config import settings
from core.engine import FALLBACK_DET_SIZE, get_engine


@dataclass
class DetectedFace:
    bbox: np.ndarray  # [x1, y1, x2, y2] in original image pixel coords
    det_score: float
    embedding: np.ndarray  # (512,) L2-normalized
    kps: np.ndarray  # 5x2 keypoints
    skipped: bool
    skip_reason: str | None = None

    @property
    def width(self) -> float:
        return float(self.bbox[2] - self.bbox[0])


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


def _tile_origins(width: int, height: int, tile_size: int, stride: int) -> list[tuple[int, int]]:
    xs = list(range(0, max(width - tile_size, 0) + 1, stride))
    ys = list(range(0, max(height - tile_size, 0) + 1, stride))
    if not xs or xs[-1] + tile_size < width:
        xs.append(max(width - tile_size, 0))
    if not ys or ys[-1] + tile_size < height:
        ys.append(max(height - tile_size, 0))
    return [(x, y) for y in ys for x in xs]


def _run_pass(image: np.ndarray, x_off: int = 0, y_off: int = 0, det_size: int | None = None) -> list[DetectedFace]:
    engine = get_engine(det_size)
    faces = engine.get(image)
    out = []
    for f in faces:
        bbox = f.bbox.copy()
        bbox[0] += x_off
        bbox[1] += y_off
        bbox[2] += x_off
        bbox[3] += y_off
        kps = f.kps.copy()
        kps[:, 0] += x_off
        kps[:, 1] += y_off
        out.append(
            DetectedFace(
                bbox=bbox,
                det_score=float(f.det_score),
                embedding=f.normed_embedding,
                kps=kps,
                skipped=False,
            )
        )
    return out


def _nms_merge(faces: list[DetectedFace], iou_thresh: float) -> list[DetectedFace]:
    faces_sorted = sorted(faces, key=lambda f: f.det_score, reverse=True)
    kept: list[DetectedFace] = []
    for f in faces_sorted:
        if any(_iou(f.bbox, k.bbox) >= iou_thresh for k in kept):
            continue
        kept.append(f)
    return kept


def detect_faces(image: np.ndarray) -> list[DetectedFace]:
    """image: BGR numpy array (as read by cv2), already EXIF-corrected."""
    height, width = image.shape[:2]
    faces = _run_pass(image)
    if not faces:
        # Likely one large close-up face (e.g. an enrollment headshot) —
        # DET_SIZE's anchors don't cover that scale. Retry smaller.
        faces = _run_pass(image, det_size=FALLBACK_DET_SIZE)

    if max(width, height) > settings.TILE_IF_LONG_SIDE_GT:
        for x, y in _tile_origins(width, height, settings.TILE_SIZE, settings.TILE_STRIDE):
            tile = image[y : y + settings.TILE_SIZE, x : x + settings.TILE_SIZE]
            tile_faces = _run_pass(tile, x_off=x, y_off=y)
            if not tile_faces:
                tile_faces = _run_pass(tile, x_off=x, y_off=y, det_size=FALLBACK_DET_SIZE)
            faces.extend(tile_faces)

    faces = _nms_merge(faces, settings.NMS_IOU)

    for f in faces:
        if f.det_score < settings.MIN_DET_SCORE:
            f.skipped = True
            f.skip_reason = f"Low detector confidence ({f.det_score:.2f})"
        elif f.width < settings.MIN_FACE_PX:
            f.skipped = True
            f.skip_reason = f"Face too small ({f.width:.0f}px)"

    return faces


def crop_face(image: np.ndarray, bbox: np.ndarray, pad: float = 0.25, min_size: int = 112) -> np.ndarray:
    """Padded crop of a face, at least min_size on the short side where the image allows."""
    height, width = image.shape[:2]
    x1, y1, x2, y2 = bbox
    w, h = x2 - x1, y2 - y1
    px, py = w * pad, h * pad
    x1 = max(int(x1 - px), 0)
    y1 = max(int(y1 - py), 0)
    x2 = min(int(x2 + px), width)
    y2 = min(int(y2 + py), height)
    return image[y1:y2, x1:x2]
