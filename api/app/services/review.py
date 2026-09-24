"""Review queue and unknown-cluster resolution actions per build-spec §9/§7.6."""

from sqlalchemy.orm import Session

from app.models import Face, Member, UnknownCluster, bytes_to_embedding
from app.services.enroll import maybe_add_confirmed_ref
from app.services.process import relabel_and_set_representatives
from app.storage.base import Storage


def _grow_ref_from_face(db: Session, storage: Storage, member: Member, face: Face) -> None:
    crop_bytes = storage.read(face.crop_key)
    embedding = bytes_to_embedding(face.embedding)
    maybe_add_confirmed_ref(db, storage, member, embedding, face.det_score, crop_bytes)


def resolve_face(db: Session, storage: Storage, face_id: str, action: str, member_id: str | None) -> Face:
    face = db.get(Face, face_id)
    if face is None:
        raise ValueError(f"Face {face_id} not found")

    if action == "confirm":
        if face.matched_member_id is None:
            raise ValueError("Cannot confirm a face with no candidate member")
        face.status = "confirmed"
        member = db.get(Member, face.matched_member_id)
        if member:
            _grow_ref_from_face(db, storage, member, face)

    elif action == "reject":
        face.status = "unknown"
        face.matched_member_id = None
        face.similarity = None
        face.cluster_id = None  # eligible for clustering again

    elif action == "assign":
        if not member_id:
            raise ValueError("assign requires member_id")
        face.status = "confirmed"
        face.matched_member_id = member_id
        face.cluster_id = None
        member = db.get(Member, member_id)
        if member:
            _grow_ref_from_face(db, storage, member, face)

    else:
        raise ValueError(f"Unknown action: {action}")

    db.commit()
    return face


def assign_cluster(db: Session, storage: Storage, cluster_id: str, member_id: str) -> UnknownCluster:
    cluster = db.get(UnknownCluster, cluster_id)
    if cluster is None:
        raise ValueError(f"Cluster {cluster_id} not found")
    member = db.get(Member, member_id)
    if member is None:
        raise ValueError(f"Member {member_id} not found")

    cluster.resolved_member_id = member_id
    faces = db.query(Face).filter(Face.cluster_id == cluster_id).all()
    for face in faces:
        face.status = "confirmed"
        face.matched_member_id = member_id
        _grow_ref_from_face(db, storage, member, face)

    db.commit()
    return cluster


def merge_cluster(db: Session, event_id: str, cluster_id: str, into_cluster_id: str) -> UnknownCluster:
    source = db.get(UnknownCluster, cluster_id)
    target = db.get(UnknownCluster, into_cluster_id)
    if source is None or target is None:
        raise ValueError("Cluster not found")

    db.query(Face).filter(Face.cluster_id == cluster_id).update({"cluster_id": into_cluster_id})
    db.delete(source)
    db.commit()

    relabel_and_set_representatives(db, event_id)
    db.refresh(target)
    return target


def dismiss_cluster(db: Session, cluster_id: str) -> UnknownCluster:
    cluster = db.get(UnknownCluster, cluster_id)
    if cluster is None:
        raise ValueError(f"Cluster {cluster_id} not found")
    cluster.dismissed = True
    db.commit()
    return cluster
