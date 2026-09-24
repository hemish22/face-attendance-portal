from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import Photo
from app.routers import auth, events, media, members, review
from core.engine import get_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    get_engine()  # load the model once at startup

    db = SessionLocal()
    try:
        db.query(Photo).filter(Photo.status == "processing").update({"status": "pending"})
        db.commit()
    finally:
        db.close()

    yield


app = FastAPI(title="Face Attendance Portal API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(members.router)
app.include_router(events.router)
app.include_router(review.router)
app.include_router(media.router)
