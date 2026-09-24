from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import current_user
from app.models import Face, Member, Photo
from app.schemas import ClusterAssignRequest, ClusterMergeRequest, ResolveFaceRequest, ReviewCandidate, ReviewFaceOut
from app.services import review as review_service
from app.storage import get_storage
from app.storage.base import Storage

router = APIRouter(tags=["review"], dependencies=[Depends(current_user)])


@router.get("/events/{event_id}/review", response_model=list[ReviewFaceOut])
def list_review_queue(event_id: str, db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    faces = (
        db.query(Face)
        .join(Photo, Photo.id == Face.photo_id)
        .filter(Photo.event_id == event_id, Face.status == "review")
        .all()
    )

    present_member_ids = {
        f.matched_member_id
        for f in db.query(Face).join(Photo, Photo.id == Face.photo_id)
        .filter(Photo.event_id == event_id, Face.status.in_(["auto", "confirmed"]))
        .all()
    }

    members = {m.id: m for m in db.query(Member).all()}

    out = []
    for f in faces:
        candidates = []
        for c in f.candidates or []:
            member = members.get(c["member_id"])
            if member is None:
                continue
            ref = None
            from app.models import MemberRef

            ref = db.query(MemberRef).filter(MemberRef.member_id == member.id).order_by(MemberRef.created_at).first()
            ref_url = storage.url(ref.photo_key, settings.MEDIA_URL_TTL_SECONDS) if ref else ""
            candidates.append(ReviewCandidate(member_id=member.id, name=member.name, score=c["score"], ref_photo_url=ref_url))

        out.append(
            ReviewFaceOut(
                face_id=f.id, photo_id=f.photo_id,
                crop_url=storage.url(f.crop_key, settings.MEDIA_URL_TTL_SECONDS),
                candidates=candidates,
            )
        )

    # members with no auto match yet first, then by score descending
    out.sort(key=lambda r: (r.candidates[0].member_id in present_member_ids if r.candidates else False, -(r.candidates[0].score if r.candidates else 0)))
    return out


@router.post("/faces/{face_id}/resolve")
def resolve_face(face_id: str, body: ResolveFaceRequest, db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    try:
        face = review_service.resolve_face(db, storage, face_id, body.action, body.member_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"face_id": face.id, "status": face.status}


@router.post("/clusters/{cluster_id}/assign")
def assign_cluster(cluster_id: str, body: ClusterAssignRequest, db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    try:
        cluster = review_service.assign_cluster(db, storage, cluster_id, body.member_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"cluster_id": cluster.id, "resolved_member_id": cluster.resolved_member_id}


@router.post("/clusters/{cluster_id}/merge")
def merge_cluster(cluster_id: str, body: ClusterMergeRequest, db: Session = Depends(get_db)):
    from app.models import UnknownCluster

    cluster = db.get(UnknownCluster, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    try:
        target = review_service.merge_cluster(db, cluster.event_id, cluster_id, body.into_cluster_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"cluster_id": target.id, "label": target.label}


@router.post("/clusters/{cluster_id}/dismiss")
def dismiss_cluster(cluster_id: str, db: Session = Depends(get_db)):
    try:
        cluster = review_service.dismiss_cluster(db, cluster_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"cluster_id": cluster.id, "dismissed": cluster.dismissed}
