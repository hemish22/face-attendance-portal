"""Event processing job per build-spec §8."""

import threading
import uuid

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.models import Event, Face, Member, MemberRef, Photo, UnknownCluster, bytes_to_embedding, embedding_to_bytes
from app.storage.base import Storage
from core.cluster import assign_to_existing_or_new, cluster_faces
from core.detect import crop_face, detect_faces
from core.match import match_faces

# One event processed at a time (a lock), per §8.
_event_lock = threading.Lock()


def _decode_bgr(stored_jpeg: bytes) -> np.ndarray:
    arr = np.frombuffer(stored_jpeg, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _active_ref_matrix(db: Session) -> tuple[np.ndarray, list[str]]:
    rows = (
        db.query(MemberRef)
        .join(Member, Member.id == MemberRef.member_id)
        .filter(Member.active.is_(True))
        .all()
    )
    if not rows:
        return np.zeros((0, 512), dtype=np.float32), []
    embeddings = np.array([bytes_to_embedding(r.embedding) for r in rows])
    member_ids = [r.member_id for r in rows]
    return embeddings, member_ids


def _detect_and_match_photo(db: Session, storage: Storage, photo: Photo, ref_matrix: np.ndarray, ref_member_ids: list[str]) -> None:
    raw = storage.read(photo.key)
    image = _decode_bgr(raw)
    height, width = image.shape[:2]

    detected = detect_faces(image)
    usable_indices = [i for i, f in enumerate(detected) if not f.skipped]

    face_rows: list[Face] = []
    for i, f in enumerate(detected):
        crop_key = f"events/{photo.event_id}/crops/{uuid.uuid4().hex}.jpg"
        if not f.skipped:
            crop = crop_face(image, f.bbox)
            _, buf = cv2.imencode(".jpg", crop)
            storage.save(crop_key, buf.tobytes())

        bbox_norm = [
            round(float(f.bbox[0] / width), 4),
            round(float(f.bbox[1] / height), 4),
            round(float(f.bbox[2] / width), 4),
            round(float(f.bbox[3] / height), 4),
        ]
        row = Face(
            photo_id=photo.id,
            bbox=bbox_norm,
            det_score=f.det_score,
            embedding=embedding_to_bytes(f.embedding),
            crop_key=crop_key,
            status="skipped" if f.skipped else "unknown",  # overwritten below for usable faces
        )
        db.add(row)
        face_rows.append(row)

    if usable_indices:
        usable_embeddings = np.array([detected[i].embedding for i in usable_indices])
        matches = match_faces(usable_embeddings, ref_matrix, ref_member_ids)
        for local_i, m in zip(usable_indices, matches):
            row = face_rows[local_i]
            row.status = m.status
            row.matched_member_id = m.member_id
            row.similarity = m.score
            row.candidates = [{"member_id": c.member_id, "score": round(c.score, 4)} for c in m.candidates]

    photo.status = "done"
    photo.n_faces = len(detected)
    db.commit()


def process_event(db: Session, storage: Storage, event_id: str) -> None:
    """Idempotent: processes only `pending` photos. Steps: detect+embed+match
    each pending photo, then cluster the unknowns, then set status='review'.
    """
    with _event_lock:
        event = db.get(Event, event_id)
        if event is None:
            raise ValueError(f"Event {event_id} not found")

        event.status = "processing"
        db.commit()

        ref_matrix, ref_member_ids = _active_ref_matrix(db)

        pending = db.query(Photo).filter(Photo.event_id == event_id, Photo.status == "pending").all()
        for photo in pending:
            photo.status = "processing"
            db.commit()
            try:
                _detect_and_match_photo(db, storage, photo, ref_matrix, ref_member_ids)
            except Exception as e:  # a failed photo must not stop the event
                photo.status = "failed"
                photo.error = str(e)
                db.commit()

        _recluster_unknowns(db, event_id)

        event.status = "review"
        db.commit()


def _recluster_unknowns(db: Session, event_id: str) -> None:
    unknown_faces = (
        db.query(Face)
        .join(Photo, Photo.id == Face.photo_id)
        .filter(Photo.event_id == event_id, Face.status == "unknown", Face.cluster_id.is_(None))
        .all()
    )
    if not unknown_faces:
        return

    existing_clusters = (
        db.query(UnknownCluster)
        .filter(UnknownCluster.event_id == event_id, UnknownCluster.dismissed.is_(False))
        .all()
    )
    existing_ids = [c.id for c in existing_clusters]
    existing_centroids = np.array([_cluster_centroid(db, c.id) for c in existing_clusters]) if existing_clusters else np.zeros((0, 512))

    new_embeddings = np.array([bytes_to_embedding(f.embedding) for f in unknown_faces])
    assignments = assign_to_existing_or_new(new_embeddings, existing_ids, existing_centroids)

    # Map temporary int labels (brand-new clusters among the leftovers) to real cluster rows.
    new_cluster_by_label: dict[int, UnknownCluster] = {}
    for face, assignment in zip(unknown_faces, assignments):
        if isinstance(assignment, str):
            face.cluster_id = assignment
            continue
        if assignment not in new_cluster_by_label:
            cluster = UnknownCluster(event_id=event_id, label="")  # label assigned after ordering
            db.add(cluster)
            db.flush()
            new_cluster_by_label[assignment] = cluster
        face.cluster_id = new_cluster_by_label[assignment].id

    db.commit()
    relabel_and_set_representatives(db, event_id)


def _cluster_centroid(db: Session, cluster_id: str) -> np.ndarray:
    faces = db.query(Face).filter(Face.cluster_id == cluster_id).all()
    embeddings = np.array([bytes_to_embedding(f.embedding) for f in faces])
    centroid = embeddings.mean(axis=0)
    return centroid / np.linalg.norm(centroid)


def relabel_and_set_representatives(db: Session, event_id: str) -> None:
    """Numbers clusters by appearance count desc, then first photo (§7.4)."""
    clusters = (
        db.query(UnknownCluster)
        .filter(UnknownCluster.event_id == event_id, UnknownCluster.dismissed.is_(False))
        .all()
    )

    def sort_key(cluster: UnknownCluster):
        faces = db.query(Face).filter(Face.cluster_id == cluster.id).all()
        count = len(faces)
        first_seen = min((f.photo_id for f in faces), default="")
        return (-count, first_seen)

    ordered = sorted(clusters, key=sort_key)
    for i, cluster in enumerate(ordered, start=1):
        cluster.label = f"Unidentified Person {i}"
        faces = db.query(Face).filter(Face.cluster_id == cluster.id).all()
        if faces:
            scored = [(f.det_score * (f.bbox[2] - f.bbox[0]), f.id) for f in faces]
            cluster.rep_face_id = max(scored)[1]
    db.commit()


def rematch_event(db: Session, storage: Storage, event_id: str) -> None:
    """Re-runs matching and clustering from stored embeddings without
    re-detecting. Skips faces a human already resolved (status='confirmed').
    """
    with _event_lock:
        ref_matrix, ref_member_ids = _active_ref_matrix(db)

        candidate_faces = (
            db.query(Face)
            .join(Photo, Photo.id == Face.photo_id)
            .filter(Photo.event_id == event_id, Face.status.in_(["auto", "review", "unknown"]))
            .all()
        )

        by_photo: dict[str, list[Face]] = {}
        for f in candidate_faces:
            by_photo.setdefault(f.photo_id, []).append(f)

        for face_rows in by_photo.values():
            embeddings = np.array([bytes_to_embedding(f.embedding) for f in face_rows])
            matches = match_faces(embeddings, ref_matrix, ref_member_ids)
            for row, m in zip(face_rows, matches):
                row.status = m.status
                row.matched_member_id = m.member_id
                row.similarity = m.score
                row.candidates = [{"member_id": c.member_id, "score": round(c.score, 4)} for c in m.candidates]
                if m.status != "unknown":
                    row.cluster_id = None
        db.commit()

        _recluster_unknowns(db, event_id)
