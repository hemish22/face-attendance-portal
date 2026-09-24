"""InsightFace singleton(s). Pure Python — no FastAPI or DB imports.

SCRFD's anchor scales are tuned relative to det_size: a large det_size (good
for finding small faces in crowd photos) makes a single close-up face (e.g.
an enrollment headshot) fall outside the anchors' covered scale range and its
score collapses to ~0. get_engine() caches one FaceAnalysis instance per
det_size so callers can fall back to a smaller det_size for close-up shots
without reloading the model from disk each time.
"""

from functools import lru_cache

from insightface.app import FaceAnalysis

from app.config import settings

# Fallback size for the "one large close-up face" case (enrollment photos).
FALLBACK_DET_SIZE = 640


@lru_cache(maxsize=4)
def get_engine(det_size: int | None = None) -> FaceAnalysis:
    size = det_size or settings.DET_SIZE
    app = FaceAnalysis(
        name="buffalo_l",
        allowed_modules=["detection", "recognition"],
        providers=["CPUExecutionProvider"],
    )
    app.prepare(ctx_id=-1, det_size=(size, size), det_thresh=0.5)
    return app
