"""Creates the first user from ADMIN_EMAIL and ADMIN_PASSWORD. Idempotent."""

from app.auth import hash_password
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import User


def main():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if existing:
            print(f"Admin user already exists: {settings.ADMIN_EMAIL}")
            return

        user = User(email=settings.ADMIN_EMAIL, password_hash=hash_password(settings.ADMIN_PASSWORD))
        db.add(user)
        db.commit()
        print(f"Created admin user: {settings.ADMIN_EMAIL}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
