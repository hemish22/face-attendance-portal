"""Retention purge per build-spec §14.

Deletes event photos, thumbs and crops of finalized events older than
--older-than days. Also deletes embeddings of `unknown` and dismissed-cluster
faces in those events. The result snapshot (event_snapshots) stays, so
exports of a purged event keep working.

Usage: python -m scripts.purge --older-than 30 [--dry-run]
"""

import argparse
from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import Event, Face, Photo, UnknownCluster, embedding_to_bytes
from app.storage import get_storage

EMPTY_EMBEDDING = embedding_to_bytes(__import__("numpy").zeros(512, dtype="float32"))


def purge(older_than_days: int, dry_run: bool = False) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    db = SessionLocal()
    storage = get_storage()

    try:
        events = (
            db.query(Event)
            .filter(Event.status == "final", Event.finalized_at.isnot(None), Event.finalized_at < cutoff)
            .all()
        )

        for event in events:
            photos = db.query(Photo).filter(Photo.event_id == event.id).all()
            faces = db.query(Face).join(Photo, Photo.id == Face.photo_id).filter(Photo.event_id == event.id).all()
            dismissed_cluster_ids = {
                c.id for c in db.query(UnknownCluster).filter(UnknownCluster.event_id == event.id, UnknownCluster.dismissed.is_(True))
            }

            print(f"Event {event.id} ({event.name}, finalized {event.finalized_at}): "
                  f"{len(photos)} photo(s), {len(faces)} face(s)")

            if dry_run:
                continue

            for photo in photos:
                storage.delete(photo.key)
                storage.delete(photo.thumb_key)

            for face in faces:
                storage.delete(face.crop_key)
                if face.status == "unknown" or face.cluster_id in dismissed_cluster_ids:
                    face.embedding = EMPTY_EMBEDDING

            db.commit()

        print(f"{'Would purge' if dry_run else 'Purged'} {len(events)} finalized event(s) older than {older_than_days} days.")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--older-than", type=int, required=True, help="Days since finalization")
    parser.add_argument("--dry-run", action="store_true", help="List what would be purged without deleting")
    args = parser.parse_args()
    purge(args.older_than, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
