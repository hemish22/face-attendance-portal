import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, get_db
from app.deps import current_user
from app.models import Event, Face, Photo
from app.schemas import EventCreate, EventOut, EventStatus, ResultResponse
from app.services.export import build_excel
from app.services.ingest import ingest_image
from app.services.process import process_event, rematch_event
from app.services.results import compute_event_results, finalize_event
from app.storage import get_storage
from app.storage.base import Storage

router = APIRouter(tags=["events"], dependencies=[Depends(current_user)])


@router.post("/events", response_model=EventOut)
def create_event(body: EventCreate, db: Session = Depends(get_db)):
    event = Event(name=body.name, date=body.date.isoformat(), status="draft")
    db.add(event)
    db.commit()
    return event


@router.get("/events", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).order_by(Event.created_at.desc()).all()


@router.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: str, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("/events/{event_id}/photos")
def upload_photos(event_id: str, files: list[UploadFile], db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    photo_ids = []
    for f in files:
        raw = f.file.read()
        stored_bytes, thumb_bytes, width, height = ingest_image(raw)
        key = f"events/{event_id}/photos/{uuid.uuid4().hex}.jpg"
        thumb_key = f"events/{event_id}/thumbs/{uuid.uuid4().hex}.jpg"
        storage.save(key, stored_bytes)
        storage.save(thumb_key, thumb_bytes)

        photo = Photo(
            event_id=event_id, key=key, thumb_key=thumb_key, filename=f.filename,
            width=width, height=height, status="pending",
        )
        db.add(photo)
        db.commit()
        photo_ids.append(photo.id)

    return {"photo_ids": photo_ids}


def _run_process(event_id: str):
    db = SessionLocal()
    try:
        process_event(db, get_storage(), event_id)
    finally:
        db.close()


def _run_rematch(event_id: str):
    db = SessionLocal()
    try:
        rematch_event(db, get_storage(), event_id)
    finally:
        db.close()


@router.post("/events/{event_id}/process")
def start_process(event_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    background_tasks.add_task(_run_process, event_id)
    return {"started": True}


@router.post("/events/{event_id}/rematch")
def start_rematch(event_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    background_tasks.add_task(_run_rematch, event_id)
    return {"started": True}


@router.get("/events/{event_id}/status", response_model=EventStatus)
def get_status(event_id: str, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    photos = db.query(Photo).filter(Photo.event_id == event_id).all()
    done = sum(1 for p in photos if p.status == "done")
    failed = sum(1 for p in photos if p.status == "failed")
    return EventStatus(stage=event.status, total=len(photos), done=done, failed=failed)


@router.get("/events/{event_id}/results", response_model=ResultResponse)
def get_results(event_id: str, db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    try:
        return compute_event_results(db, storage, event_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/events/{event_id}/export")
def export_event(event_id: str, format: str = "json", db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    try:
        result = compute_event_results(db, storage, event_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if format == "json":
        return result

    if format == "xlsx":
        thresholds = {
            "T_HIGH": settings.T_HIGH, "T_LOW": settings.T_LOW, "T_CLUSTER": settings.T_CLUSTER,
            "MIN_AUTO_PHOTOS": settings.MIN_AUTO_PHOTOS,
        }
        data = build_excel(result, thresholds)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="event_{event_id}.xlsx"'},
        )

    raise HTTPException(status_code=400, detail="format must be json or xlsx")


@router.post("/events/{event_id}/finalize", response_model=ResultResponse)
def finalize(event_id: str, db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    try:
        return finalize_event(db, storage, event_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/photos/{photo_id}/faces")
def get_photo_faces(photo_id: str, db: Session = Depends(get_db)):
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    faces = db.query(Face).filter(Face.photo_id == photo_id).all()
    return [
        {"face_id": f.id, "bbox": f.bbox, "status": f.status, "member_id": f.matched_member_id, "score": f.similarity}
        for f in faces
    ]
