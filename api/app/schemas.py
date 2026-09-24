from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --- auth ---


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str


# --- members ---


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    roll_no: str
    name: str
    dept: str | None = None
    year: str | None = None
    consent_at: datetime | None = None
    active: bool
    ref_count: int = 0
    created_at: datetime


class MemberFileResult(BaseModel):
    filename: str
    accepted: bool
    reason: str | None = None


class MemberCreateResponse(BaseModel):
    member: MemberOut
    files: list[MemberFileResult]


class MemberRefOut(BaseModel):
    id: str
    source: Literal["enroll", "confirmed"]
    photo_url: str
    det_score: float
    created_at: datetime


# --- events ---


class EventCreate(BaseModel):
    name: str
    date: date


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    date: str
    status: Literal["draft", "processing", "review", "final"]
    created_at: datetime
    finalized_at: datetime | None = None


class EventStatus(BaseModel):
    stage: str
    total: int
    done: int
    failed: int


# --- review / clusters ---


class ResolveFaceRequest(BaseModel):
    action: Literal["confirm", "reject", "assign"]
    member_id: str | None = None


class ClusterAssignRequest(BaseModel):
    member_id: str


class ClusterMergeRequest(BaseModel):
    into_cluster_id: str


class ReviewCandidate(BaseModel):
    member_id: str
    name: str
    score: float
    ref_photo_url: str


class ReviewFaceOut(BaseModel):
    face_id: str
    photo_id: str
    crop_url: str
    candidates: list[ReviewCandidate]


# --- result JSON (§9) ---


class PhotoMatch(BaseModel):
    photo_id: str
    filename: str
    bbox: list[float] = Field(min_length=4, max_length=4)
    score: float
    status: Literal["auto", "review", "confirmed", "unknown"]


class PersonResult(BaseModel):
    member_id: str
    roll_no: str
    name: str
    best_score: float
    photos_matched: int
    photos: list[PhotoMatch]


class AbsentMember(BaseModel):
    member_id: str
    roll_no: str
    name: str


class UnidentifiedPhoto(BaseModel):
    photo_id: str
    filename: str
    bbox: list[float] = Field(min_length=4, max_length=4)


class UnidentifiedCluster(BaseModel):
    cluster_id: str
    label: str
    appearances: int
    crop_url: str | None = None
    photos: list[UnidentifiedPhoto]


class PhotoPerson(BaseModel):
    label: str
    member_id: str | None = None
    bbox: list[float] = Field(min_length=4, max_length=4)
    status: Literal["auto", "confirmed", "review", "unknown"]


class PhotoIndexEntry(BaseModel):
    photo_id: str
    filename: str
    photo_url: str | None = None
    thumb_url: str | None = None
    people: list[PhotoPerson]


class EventSummary(BaseModel):
    members: int
    present: int
    needs_review: int
    absent: int
    unidentified: int
    photos: int
    faces_detected: int
    faces_skipped_low_quality: int


class EventInfo(BaseModel):
    id: str
    name: str
    date: str
    status: Literal["draft", "processing", "review", "final"]


class ResultResponse(BaseModel):
    event: EventInfo
    summary: EventSummary
    present: list[PersonResult]
    needs_review: list[PersonResult]
    absent: list[AbsentMember]
    unidentified: list[UnidentifiedCluster]
    photos: list[PhotoIndexEntry]
