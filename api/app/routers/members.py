import csv
import io
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import current_user
from app.models import Face, Member, MemberRef
from app.schemas import MemberCreateResponse, MemberFileResult, MemberOut, MemberRefOut
from app.services.enroll import enroll_photo
from app.storage import get_storage
from app.storage.base import Storage

router = APIRouter(tags=["members"], dependencies=[Depends(current_user)])


def _to_out(db: Session, member: Member) -> MemberOut:
    ref_count = db.query(MemberRef).filter(MemberRef.member_id == member.id).count()
    return MemberOut.model_validate({**member.__dict__, "ref_count": ref_count})


@router.get("/members", response_model=list[MemberOut])
def list_members(db: Session = Depends(get_db)):
    members = db.query(Member).order_by(Member.name).all()
    return [_to_out(db, m) for m in members]


@router.post("/members", response_model=MemberCreateResponse)
def create_member(
    roll_no: str = Form(...),
    name: str = Form(...),
    dept: str | None = Form(None),
    year: str | None = Form(None),
    consent: bool = Form(...),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    if not consent:
        raise HTTPException(status_code=400, detail="Consent is required to enroll a member")

    if db.query(Member).filter(Member.roll_no == roll_no).first():
        raise HTTPException(status_code=409, detail=f"Member with roll_no {roll_no} already exists")

    member = Member(roll_no=roll_no, name=name, dept=dept, year=year, consent_at=datetime.now(timezone.utc), active=True)
    db.add(member)
    db.commit()

    results = []
    for f in files:
        raw = f.file.read()
        accepted, reason = enroll_photo(db, storage, member, raw, f.filename)
        results.append(MemberFileResult(filename=f.filename, accepted=accepted, reason=reason))

    return MemberCreateResponse(member=_to_out(db, member), files=results)


@router.post("/members/import", response_model=list[MemberCreateResponse])
def import_members(
    csv_file: UploadFile = File(...),
    photos_zip: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    reader = csv.DictReader(io.StringIO(csv_file.file.read().decode("utf-8")))
    rows = list(reader)

    zf = zipfile.ZipFile(io.BytesIO(photos_zip.file.read()))
    photos_by_roll: dict[str, list[str]] = {}
    for name in zf.namelist():
        stem = name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        roll_no = stem.rsplit("_", 1)[0] if stem[-1].isdigit() and "_" in stem else stem
        photos_by_roll.setdefault(roll_no, []).append(name)

    responses = []
    for row in rows:
        roll_no = row["roll_no"]
        if db.query(Member).filter(Member.roll_no == roll_no).first():
            continue
        member = Member(
            roll_no=roll_no, name=row["name"], dept=row.get("dept"), year=row.get("year"),
            consent_at=datetime.now(timezone.utc), active=True,
        )
        db.add(member)
        db.commit()

        results = []
        for zname in photos_by_roll.get(roll_no, []):
            raw = zf.read(zname)
            accepted, reason = enroll_photo(db, storage, member, raw, zname)
            results.append(MemberFileResult(filename=zname, accepted=accepted, reason=reason))

        responses.append(MemberCreateResponse(member=_to_out(db, member), files=results))

    return responses


@router.get("/members/{member_id}", response_model=MemberOut)
def get_member(member_id: str, db: Session = Depends(get_db)):
    member = db.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return _to_out(db, member)


@router.get("/members/{member_id}/refs", response_model=list[MemberRefOut])
def list_member_refs(member_id: str, db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    refs = db.query(MemberRef).filter(MemberRef.member_id == member_id).order_by(MemberRef.created_at).all()
    return [
        MemberRefOut(
            id=r.id, source=r.source, det_score=r.det_score, created_at=r.created_at,
            photo_url=storage.url(r.photo_key, settings.MEDIA_URL_TTL_SECONDS),
        )
        for r in refs
    ]


@router.post("/members/{member_id}/refs", response_model=list[MemberFileResult])
def add_member_refs(
    member_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    member = db.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    results = []
    for f in files:
        raw = f.file.read()
        accepted, reason = enroll_photo(db, storage, member, raw, f.filename)
        results.append(MemberFileResult(filename=f.filename, accepted=accepted, reason=reason))
    return results


@router.delete("/members/{member_id}/refs/{ref_id}")
def delete_member_ref(member_id: str, ref_id: str, db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    ref = db.query(MemberRef).filter(MemberRef.id == ref_id, MemberRef.member_id == member_id).first()
    if ref is None:
        raise HTTPException(status_code=404, detail="Reference photo not found")
    storage.delete(ref.photo_key)
    db.delete(ref)
    db.commit()
    return {"deleted": True}


@router.delete("/members/{member_id}")
def delete_member(member_id: str, db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    member = db.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    for ref in db.query(MemberRef).filter(MemberRef.member_id == member_id).all():
        storage.delete(ref.photo_key)

    db.query(Face).filter(Face.matched_member_id == member_id).update(
        {"matched_member_id": None, "status": "unknown", "similarity": None}
    )

    db.delete(member)  # cascades to member_refs
    db.commit()
    return {"deleted": True}
