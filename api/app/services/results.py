"""Aggregation per build-spec §7.5, computed on read."""

from collections import defaultdict

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Event, EventSnapshot, Face, Member, Photo, UnknownCluster


def _photo_urls(storage, photo: Photo) -> tuple[str, str]:
    return storage.url(photo.key, settings.MEDIA_URL_TTL_SECONDS), storage.url(photo.thumb_key, settings.MEDIA_URL_TTL_SECONDS)


def compute_event_results(db: Session, storage, event_id: str) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise ValueError(f"Event {event_id} not found")

    if event.status == "final":
        snapshot = db.get(EventSnapshot, event_id)
        if snapshot is not None:
            return snapshot.json

    photos = db.query(Photo).filter(Photo.event_id == event_id).order_by(Photo.filename).all()
    photo_by_id = {p.id: p for p in photos}

    faces = (
        db.query(Face)
        .join(Photo, Photo.id == Face.photo_id)
        .filter(Photo.event_id == event_id)
        .all()
    )

    members = {m.id: m for m in db.query(Member).filter(Member.active.is_(True)).all()}
    clusters = {c.id: c for c in db.query(UnknownCluster).filter(UnknownCluster.event_id == event_id).all()}

    present_photos: dict[str, list[dict]] = defaultdict(list)
    review_photos: dict[str, list[dict]] = defaultdict(list)
    photo_people: dict[str, list[dict]] = defaultdict(list)
    cluster_photos: dict[str, list[dict]] = defaultdict(list)

    faces_detected = sum(p.n_faces for p in photos)
    faces_skipped = sum(1 for f in faces if f.status == "skipped")

    for face in faces:
        if face.status == "skipped":
            continue
        photo = photo_by_id[face.photo_id]
        _, thumb_url = _photo_urls(storage, photo)
        base = {"photo_id": photo.id, "filename": photo.filename, "bbox": face.bbox}

        if face.status in ("auto", "confirmed") and face.matched_member_id:
            member = members.get(face.matched_member_id)
            if member is None:
                continue
            present_photos[member.id].append({**base, "score": round(face.similarity or 1.0, 4), "status": face.status})
            photo_people[photo.id].append({"label": member.name, "member_id": member.id, "bbox": face.bbox, "status": face.status})

        elif face.status == "review" and face.matched_member_id:
            member = members.get(face.matched_member_id)
            if member is None:
                continue
            review_photos[member.id].append({**base, "score": round(face.similarity or 0.0, 4), "status": "review"})
            photo_people[photo.id].append({"label": member.name, "member_id": member.id, "bbox": face.bbox, "status": "review"})

        elif face.status == "unknown":
            cluster = clusters.get(face.cluster_id) if face.cluster_id else None
            if cluster is None or cluster.dismissed:
                continue
            if cluster.resolved_member_id:
                member = members.get(cluster.resolved_member_id)
                if member is None:
                    continue
                present_photos[member.id].append({**base, "score": round(face.similarity or 1.0, 4), "status": "confirmed"})
                photo_people[photo.id].append({"label": member.name, "member_id": member.id, "bbox": face.bbox, "status": "confirmed"})
            else:
                cluster_photos[cluster.id].append(base)
                photo_people[photo.id].append({"label": cluster.label, "member_id": None, "bbox": face.bbox, "status": "unknown"})

    present_list = []
    review_list = []
    for member in members.values():
        p_photos = present_photos.get(member.id, [])
        r_photos = review_photos.get(member.id, [])
        if len(p_photos) >= settings.MIN_AUTO_PHOTOS:
            best = max((p["score"] for p in p_photos), default=0.0)
            present_list.append(
                {"member_id": member.id, "roll_no": member.roll_no, "name": member.name,
                 "best_score": best, "photos_matched": len(p_photos), "photos": p_photos + r_photos}
            )
        elif r_photos:
            best = max((p["score"] for p in r_photos), default=0.0)
            review_list.append(
                {"member_id": member.id, "roll_no": member.roll_no, "name": member.name,
                 "best_score": best, "photos_matched": len(r_photos), "photos": r_photos}
            )

    present_ids = {p["member_id"] for p in present_list}
    review_ids = {p["member_id"] for p in review_list}
    absent_list = [
        {"member_id": m.id, "roll_no": m.roll_no, "name": m.name}
        for m in members.values()
        if m.id not in present_ids and m.id not in review_ids
    ]

    unidentified = []
    for cluster in clusters.values():
        if cluster.dismissed or cluster.resolved_member_id:
            continue
        photos_for_cluster = cluster_photos.get(cluster.id, [])
        if not photos_for_cluster:
            continue
        crop_key = _rep_crop_key(db, cluster) if cluster.rep_face_id else None
        crop_url = storage.url(crop_key, settings.MEDIA_URL_TTL_SECONDS) if crop_key else None
        unidentified.append(
            {"cluster_id": cluster.id, "label": cluster.label, "appearances": len(photos_for_cluster),
             "crop_url": crop_url, "photos": photos_for_cluster}
        )
    unidentified.sort(key=lambda c: -c["appearances"])

    photos_out = []
    for p in photos:
        photo_url, thumb_url = _photo_urls(storage, p)
        photos_out.append(
            {"photo_id": p.id, "filename": p.filename, "photo_url": photo_url, "thumb_url": thumb_url,
             "people": photo_people.get(p.id, [])}
        )

    return {
        "event": {"id": event.id, "name": event.name, "date": event.date, "status": event.status},
        "summary": {
            "members": len(members), "present": len(present_list), "needs_review": len(review_list),
            "absent": len(absent_list), "unidentified": len(unidentified), "photos": len(photos),
            "faces_detected": faces_detected, "faces_skipped_low_quality": faces_skipped,
        },
        "present": present_list,
        "needs_review": review_list,
        "absent": absent_list,
        "unidentified": unidentified,
        "photos": photos_out,
    }


def _rep_crop_key(db: Session, cluster: UnknownCluster) -> str | None:
    face = db.get(Face, cluster.rep_face_id)
    return face.crop_key if face else None


def finalize_event(db: Session, storage, event_id: str) -> dict:
    from datetime import datetime, timezone

    event = db.get(Event, event_id)
    if event is None:
        raise ValueError(f"Event {event_id} not found")

    result = compute_event_results(db, storage, event_id)
    event.status = "final"
    event.finalized_at = datetime.now(timezone.utc)
    result["event"]["status"] = "final"

    snapshot = db.get(EventSnapshot, event_id)
    if snapshot is None:
        snapshot = EventSnapshot(event_id=event_id, json=result)
        db.add(snapshot)
    else:
        snapshot.json = result

    db.commit()
    return result
