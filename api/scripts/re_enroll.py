"""Re-enroll members from a folder of original, un-retouched photos.

The existing member reference photos came from the club website and were
AI-enhanced ("made professional"); those fingerprints match the raw event
photos poorly, so some people are missed. This script rebuilds the reference
set from the original good-quality photos instead.

Photo naming (any mix is fine):

    HEMISH_JAIN.jpg      roll_no from the roster (underscores, case-insensitive)
    hemish_jain.jpg      full name, snake_case
    hemish.jpg           just a first name (must be unique among members)
    hemish_1.jpg, hemish_2.jpg   more than one photo of the same person

Members are resolved with a purely textual matcher (no photos are compared
during resolution): the stem is split into words and matched against the
members table by roll_no / full-name / unique first-or-last name. Photos that
resolve to nobody, resolve to more than one member, or fail the enrollment
quality gate are reported and skipped.

For every matched member the old website refs are deleted (DB rows + stored
jpgs) and replaced by refs built from their named originals through the
standard enrollment gate. With --rematch, the existing events are then
re-matched against the new refs.

Usage (from api/):

    python -m scripts.re_enroll --src ../../photos2 --dry-run
    python -m scripts.re_enroll --src ../../photos2 --rematch
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

from app.db import SessionLocal
from app.models import Event, Member, MemberRef
from app.services.enroll import enroll_photo
from app.services.process import rematch_event
from app.storage import get_storage

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")


def _word_tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def _load_member_index(db) -> list[dict]:
    index = []
    for m in db.query(Member).all():
        tokens = _word_tokens(m.name)
        index.append(
            {
                "id": m.id,
                "roll_no": m.roll_no,
                "name": m.name,
                "name_tokens": set(tokens),
            }
        )
    return index


def resolve_member(stem: str, index: list[dict], path_name: str) -> tuple[dict | None, str]:
    """Returns (member, reason). reason is a short tag: 'roll_no'|'name'|'ambiguous'|'unknown'."""
    tokens = [re.sub(r"\d+$", "", t) for t in _word_tokens(stem)]
    tokens = [t for t in tokens if t and not t.isdigit()]
    if not tokens:
        return None, "unknown"

    candidates = [m for m in index if set(tokens) <= m["name_tokens"]]

    if len(candidates) == 1:
        return candidates[0], "name"

    if len(candidates) > 1:
        names = ", ".join(sorted(m["name"] for m in candidates))
        print(f"  SKIP  {path_name}: ambiguous ('{stem}' could be any of: {names})")
        return None, "ambiguous"

    print(f"  SKIP  {path_name}: no member matches '{stem}'")
    return None, "unknown"


def _clear_member_refs(db, storage, member_id: str) -> int:
    refs = db.query(MemberRef).filter(MemberRef.member_id == member_id).all()
    for ref in refs:
        storage.delete(ref.photo_key)
    db.query(MemberRef).filter(MemberRef.member_id == member_id).delete()
    db.commit()
    return len(refs)


def re_enroll(folder: Path, dry_run: bool, do_rematch: bool) -> None:
    photo_paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    if not photo_paths:
        print(f"No images found in {folder}")
        return

    db = SessionLocal()
    storage = get_storage()
    try:
        index = _load_member_index(db)

        by_member: dict[str, list[Path]] = defaultdict(list)
        for path in photo_paths:
            member, _reason = resolve_member(path.stem, index, path.name)
            if member:
                by_member[member["id"]].append(path)

        print(f"\n{len(photo_paths)} photo(s), {len(by_member)} member(s) matched.\n")

        count_before = db.query(MemberRef).count()
        enrolled_members = 0
        total_accepted = 0
        total_rejected = 0

        for member in db.query(Member).order_by(Member.name).all():
            photos = by_member.get(member.id)
            if not photos:
                continue

            enrolled_members += 1
            if dry_run:
                print(f"  DRY-RUN {member.roll_no} ({member.name}): would clear old refs, "
                      f"enroll from {len(photos)} original photo(s)")
                continue

            cleared = _clear_member_refs(db, storage, member.id)
            for path in photos:
                accepted, reason = enroll_photo(db, storage, member, path.read_bytes(), path.name)
                if accepted:
                    total_accepted += 1
                    print(f"  OK     {member.roll_no:24s} <- {path.name}")
                else:
                    total_rejected += 1
                    print(f"  REJECT {member.roll_no:24s} <- {path.name}: {reason}")
            print(f"  * removed {cleared} old ref(s) for {member.roll_no}")

        if dry_run:
            print(f"\nDry run complete: would re-enroll {enrolled_members} member(s) from "
                  f"{len(photo_paths)} photo(s). No changes made.")
            return

        print(f"\nRe-enrolled {enrolled_members} member(s): {total_accepted} ref(s) added, "
              f"{total_rejected} rejected by the quality gate.")

        missing = [
            m.roll_no
            for m in db.query(Member).all()
            if db.query(MemberRef).filter(MemberRef.member_id == m.id).count() == 0
        ]
        if missing:
            print(f"  Members with no reference photos after this run: {', '.join(sorted(missing))}")

        if do_rematch:
            events = db.query(Event).filter(Event.status != "final").all()
            print(f"\nRe-matching {len(events)} event(s) against the new refs...")
            for event in events:
                print(f"  rematch {event.name} ({event.id})")
                rematch_event(db, storage, event.id)
            print("Rematch done.")

        print(f"\nDB refs before: {count_before}, after: {db.query(MemberRef).count()}.")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Re-enroll members from named original photos")
    parser.add_argument("--src", required=True, help="Folder containing the renamed original photos")
    parser.add_argument("--dry-run", action="store_true", help="Show the matching plan without changing anything")
    parser.add_argument("--rematch", action="store_true", help="Re-match existing events after re-enrolling")
    args = parser.parse_args()

    re_enroll(Path(args.src), dry_run=args.dry_run, do_rematch=args.rematch)


if __name__ == "__main__":
    main()