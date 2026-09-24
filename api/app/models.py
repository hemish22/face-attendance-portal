import uuid
from datetime import datetime

import numpy as np
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_id() -> str:
    return uuid.uuid4().hex


def embedding_to_bytes(embedding: np.ndarray) -> bytes:
    return embedding.astype(np.float32).tobytes()


def bytes_to_embedding(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype=np.float32)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Member(Base):
    __tablename__ = "members"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    roll_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dept: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[str | None] = mapped_column(String(32), nullable=True)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    refs: Mapped[list["MemberRef"]] = relationship(back_populates="member", cascade="all, delete-orphan")


class MemberRef(Base):
    __tablename__ = "member_refs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), nullable=False)
    embedding: Mapped[bytes] = mapped_column(LargeBinary(2048), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # enroll | confirmed
    photo_key: Mapped[str] = mapped_column(String(512), nullable=False)
    det_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    member: Mapped[Member] = relationship(back_populates="refs")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|processing|review|final
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    photos: Mapped[list["Photo"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    clusters: Mapped[list["UnknownCluster"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(512), nullable=False)
    thumb_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|processing|done|failed
    n_faces: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(512), nullable=True)

    event: Mapped[Event] = relationship(back_populates="photos")
    faces: Mapped[list["Face"]] = relationship(back_populates="photo", cascade="all, delete-orphan")


class Face(Base):
    __tablename__ = "faces"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    photo_id: Mapped[str] = mapped_column(ForeignKey("photos.id"), nullable=False)
    bbox: Mapped[list] = mapped_column(JSON, nullable=False)  # [x1,y1,x2,y2] normalized 0-1
    det_score: Mapped[float] = mapped_column(Float, nullable=False)
    embedding: Mapped[bytes] = mapped_column(LargeBinary(2048), nullable=False)
    crop_key: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # auto|review|confirmed|unknown|skipped
    matched_member_id: Mapped[str | None] = mapped_column(ForeignKey("members.id"), nullable=True)
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidates: Mapped[list | None] = mapped_column(JSON, nullable=True)  # top-3 [{member_id, score}]
    cluster_id: Mapped[str | None] = mapped_column(ForeignKey("unknown_clusters.id"), nullable=True)

    photo: Mapped[Photo] = relationship(back_populates="faces")


class UnknownCluster(Base):
    __tablename__ = "unknown_clusters"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    # Not a real FK: faces.cluster_id -> unknown_clusters.id already covers
    # that edge, and a FK the other way makes the two tables' creation order
    # circular (SQLite tolerates it, Postgres rejects it at migration time).
    rep_face_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolved_member_id: Mapped[str | None] = mapped_column(ForeignKey("members.id"), nullable=True)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)

    event: Mapped[Event] = relationship(back_populates="clusters")


class EventSnapshot(Base):
    __tablename__ = "event_snapshots"

    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), primary_key=True)
    json: Mapped[dict] = mapped_column(JSON, nullable=False)
