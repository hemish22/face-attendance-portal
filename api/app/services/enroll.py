import uuid

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Member, MemberRef, bytes_to_embedding, embedding_to_bytes
from app.services.ingest import ingest_image
from app.storage.base import Storage
from core.detect import detect_faces
from core.quality import check_enrollment_quality, is_duplicate


def _decode_bgr(stored_jpeg: bytes) -> np.ndarray:
    arr = np.frombuffer(stored_jpeg, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _other_members_ref_matrix(db: Session, member_id: str) -> np.ndarray:
    rows = db.query(MemberRef).filter(MemberRef.member_id != member_id).all()
    if not rows:
        return np.zeros((0, 512), dtype=np.float32)
    return np.array([bytes_to_embedding(r.embedding) for r in rows])


def enroll_photo(db: Session, storage: Storage, member: Member, raw: bytes, filename: str) -> tuple[bool, str | None]:
    """Ingests, quality-gates and (if accepted) stores one enrollment photo as a ref.

    Returns (accepted, reason). reason is set on rejection.
    """
    existing_ref_count = db.query(MemberRef).filter(MemberRef.member_id == member.id).count()
    if existing_ref_count >= settings.MAX_REFS_PER_MEMBER:
        return False, f"Member already has the maximum {settings.MAX_REFS_PER_MEMBER} reference photos"

    stored_bytes, _thumb_bytes, _width, _height = ingest_image(raw)
    image = _decode_bgr(stored_bytes)

    faces = detect_faces(image)
    quality = check_enrollment_quality(faces, image)
    if not quality.ok:
        return False, quality.reason

    face = faces[0]
    other_refs = _other_members_ref_matrix(db, member.id)
    if is_duplicate(face.embedding, other_refs, threshold=0.6):
        return False, "Possible duplicate or wrong person: matches another member's reference photo"

    key = f"enroll/{member.id}/{uuid.uuid4().hex}.jpg"
    storage.save(key, stored_bytes)

    ref = MemberRef(
        member_id=member.id,
        embedding=embedding_to_bytes(face.embedding),
        source="enroll",
        photo_key=key,
        det_score=face.det_score,
    )
    db.add(ref)
    db.commit()
    return True, None


def maybe_add_confirmed_ref(
    db: Session,
    storage: Storage,
    member: Member,
    embedding: np.ndarray,
    det_score: float,
    crop_bytes: bytes,
) -> bool:
    """Reference growth per §7.6: add a confirmed crop as a new ref if it
    clears the quality bar, isn't a near-duplicate of an existing ref, and
    the member isn't already at MAX_REFS_PER_MEMBER. Returns whether added.
    """
    if det_score < 0.8:
        return False

    existing = db.query(MemberRef).filter(MemberRef.member_id == member.id).all()
    if len(existing) >= settings.MAX_REFS_PER_MEMBER:
        return False

    if existing:
        existing_matrix = np.array([bytes_to_embedding(r.embedding) for r in existing])
        if float((existing_matrix @ embedding).max()) > 0.95:
            return False

    key = f"enroll/{member.id}/{uuid.uuid4().hex}.jpg"
    storage.save(key, crop_bytes)

    ref = MemberRef(
        member_id=member.id,
        embedding=embedding_to_bytes(embedding),
        source="confirmed",
        photo_key=key,
        det_score=det_score,
    )
    db.add(ref)
    db.commit()
    return True
