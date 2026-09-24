"""M1 done-check CLI: takes an enrollment folder and an event folder, writes
the §9 result JSON.

Enrollment folder layout:
    <enroll_dir>/roster.csv          # roll_no,name,dept (dept optional)
    <enroll_dir>/<roll_no_lower>.jpg # one or more enrollment photos per member

Event folder layout:
    <event_dir>/*.jpg | *.png        # event photos, any filenames

Usage:
    python -m scripts.run_event --enroll-dir <dir> --event-dir <dir> --out result.json
"""

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.config import settings
from core.cluster import cluster_faces, order_clusters, representative_index
from core.detect import DetectedFace, crop_face, detect_faces
from core.match import match_faces


def glob_images(directory: Path) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))


def load_exif_corrected_bgr(path: Path) -> np.ndarray:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def slug_to_roll(path: Path) -> str:
    return path.stem.upper()


def enroll_members(enroll_dir: Path) -> tuple[dict, list[str], list[str], np.ndarray]:
    """Returns (members_by_roll, ref_member_ids, ref_photo_names, ref_embeddings)."""
    members_by_roll = {}
    with open(enroll_dir / "roster.csv") as f:
        for row in csv.DictReader(f):
            members_by_roll[row["roll_no"]] = {"name": row["name"], "dept": row.get("dept", "")}

    ref_member_ids: list[str] = []
    ref_photo_names: list[str] = []
    ref_embeddings: list[np.ndarray] = []

    for photo_path in glob_images(enroll_dir):
        roll_no = slug_to_roll(photo_path)
        if roll_no not in members_by_roll:
            continue

        image = load_exif_corrected_bgr(photo_path)
        faces = [f for f in detect_faces(image) if not f.skipped]

        if len(faces) != 1:
            print(f"  REJECT {photo_path.name}: expected exactly one face, found {len(faces)}")
            continue
        face = faces[0]
        if face.det_score < settings.ENROLL_MIN_DET:
            print(f"  REJECT {photo_path.name}: detection confidence too low ({face.det_score:.2f})")
            continue
        if face.width < settings.ENROLL_MIN_FACE_PX:
            print(f"  REJECT {photo_path.name}: face too small ({face.width:.0f}px)")
            continue

        ref_member_ids.append(roll_no)
        ref_photo_names.append(photo_path.name)
        ref_embeddings.append(face.embedding)
        print(f"  OK {photo_path.name} -> {roll_no} ({members_by_roll[roll_no]['name']}), det_score={face.det_score:.2f}")

    ref_matrix = np.array(ref_embeddings) if ref_embeddings else np.zeros((0, 512))
    return members_by_roll, ref_member_ids, ref_photo_names, ref_matrix


def process_event(event_dir: Path, ref_member_ids: list[str], ref_matrix: np.ndarray):
    photos = []
    all_unknown = []  # list of dicts: {photo_idx, face, embedding}
    per_photo_matches = []  # list of (photo_meta, [(face, match_result)])

    photo_paths = glob_images(event_dir)
    faces_skipped_low_quality = 0
    faces_detected = 0

    for photo_idx, photo_path in enumerate(photo_paths):
        image = load_exif_corrected_bgr(photo_path)
        height, width = image.shape[:2]
        detected = detect_faces(image)
        faces_detected += len(detected)

        usable = [f for f in detected if not f.skipped]
        faces_skipped_low_quality += len(detected) - len(usable)

        photo_meta = {"photo_id": str(photo_idx), "filename": photo_path.name, "width": width, "height": height}
        photos.append(photo_meta)

        if not usable:
            per_photo_matches.append((photo_meta, []))
            continue

        embeddings = np.array([f.embedding for f in usable])
        matches = match_faces(embeddings, ref_matrix, ref_member_ids)
        per_photo_matches.append((photo_meta, list(zip(usable, matches))))

        for face, m in zip(usable, matches):
            if m.status == "unknown":
                all_unknown.append({"photo_idx": photo_idx, "face": face})

    return photos, per_photo_matches, all_unknown, faces_detected, faces_skipped_low_quality


def normalize_bbox(bbox: np.ndarray, width: int, height: int) -> list[float]:
    x1, y1, x2, y2 = bbox
    return [round(float(x1 / width), 4), round(float(y1 / height), 4), round(float(x2 / width), 4), round(float(y2 / height), 4)]


def build_result(event_name: str, event_date: str, members_by_roll: dict, photos, per_photo_matches, all_unknown, faces_detected, faces_skipped):
    present = {}
    needs_review = {}
    photo_by_id = {p["photo_id"]: p for p in photos}
    photo_people = defaultdict(list)

    for photo_meta, matched in per_photo_matches:
        w, h = photo_meta["width"], photo_meta["height"]
        for face, m in matched:
            if m.status in ("auto",):
                bucket = present.setdefault(m.member_id, {"photos": [], "best_score": 0.0})
                bucket["photos"].append(
                    {"photo_id": photo_meta["photo_id"], "filename": photo_meta["filename"],
                     "bbox": normalize_bbox(face.bbox, w, h), "score": round(m.score, 4), "status": "auto"}
                )
                bucket["best_score"] = max(bucket["best_score"], m.score)
                photo_people[photo_meta["photo_id"]].append(
                    {"label": members_by_roll[m.member_id]["name"], "member_id": m.member_id,
                     "bbox": normalize_bbox(face.bbox, w, h), "status": "auto"}
                )
            elif m.status == "review":
                bucket = needs_review.setdefault(m.member_id, {"photos": [], "best_score": 0.0})
                bucket["photos"].append(
                    {"photo_id": photo_meta["photo_id"], "filename": photo_meta["filename"],
                     "bbox": normalize_bbox(face.bbox, w, h), "score": round(m.score, 4), "status": "review"}
                )
                bucket["best_score"] = max(bucket["best_score"], m.score)
                photo_people[photo_meta["photo_id"]].append(
                    {"label": members_by_roll[m.member_id]["name"], "member_id": m.member_id,
                     "bbox": normalize_bbox(face.bbox, w, h), "status": "review"}
                )

    # Unknown clustering
    unidentified = []
    if all_unknown:
        embeddings = np.array([u["face"].embedding for u in all_unknown])
        labels = cluster_faces(embeddings)
        by_cluster = defaultdict(list)
        for u, label in zip(all_unknown, labels):
            by_cluster[int(label)].append(u)

        counts = {k: len(v) for k, v in by_cluster.items()}
        first_seen = {k: min(u["photo_idx"] for u in v) for k, v in by_cluster.items()}
        order = order_clusters(counts, first_seen)

        for display_i, cluster_key in enumerate(order, start=1):
            members_in_cluster = by_cluster[cluster_key]
            det_scores = np.array([u["face"].det_score for u in members_in_cluster])
            widths = np.array([u["face"].width for u in members_in_cluster])
            rep_i = representative_index(det_scores, widths)
            rep_face = members_in_cluster[rep_i]["face"]
            label = f"Unidentified Person {display_i}"

            cluster_photos = []
            for u in members_in_cluster:
                photo_meta = photos[u["photo_idx"]]
                w, h = photo_meta["width"], photo_meta["height"]
                bbox_norm = normalize_bbox(u["face"].bbox, w, h)
                cluster_photos.append({"photo_id": photo_meta["photo_id"], "filename": photo_meta["filename"], "bbox": bbox_norm})
                photo_people[photo_meta["photo_id"]].append(
                    {"label": label, "member_id": None, "bbox": bbox_norm, "status": "unknown"}
                )

            unidentified.append(
                {"cluster_id": str(cluster_key), "label": label, "appearances": len(members_in_cluster),
                 "crop_url": None, "photos": cluster_photos}
            )

    present_list = [
        {"member_id": mid, "roll_no": mid, "name": members_by_roll[mid]["name"],
         "best_score": round(v["best_score"], 4), "photos_matched": len(v["photos"]), "photos": v["photos"]}
        for mid, v in present.items()
        if len(v["photos"]) >= settings.MIN_AUTO_PHOTOS
    ]
    present_ids = {p["member_id"] for p in present_list}

    needs_review_list = [
        {"member_id": mid, "roll_no": mid, "name": members_by_roll[mid]["name"],
         "best_score": round(v["best_score"], 4), "photos_matched": len(v["photos"]), "photos": v["photos"]}
        for mid, v in needs_review.items()
        if mid not in present_ids
    ]
    review_ids = {p["member_id"] for p in needs_review_list}

    absent_list = [
        {"member_id": mid, "roll_no": mid, "name": info["name"]}
        for mid, info in members_by_roll.items()
        if mid not in present_ids and mid not in review_ids
    ]

    photos_out = [
        {"photo_id": p["photo_id"], "filename": p["filename"], "people": photo_people.get(p["photo_id"], [])}
        for p in photos
    ]

    return {
        "event": {"id": "local-run", "name": event_name, "date": event_date, "status": "review"},
        "summary": {
            "members": len(members_by_roll), "present": len(present_list), "needs_review": len(needs_review_list),
            "absent": len(absent_list), "unidentified": len(unidentified), "photos": len(photos),
            "faces_detected": faces_detected, "faces_skipped_low_quality": faces_skipped,
        },
        "present": present_list,
        "needs_review": needs_review_list,
        "absent": absent_list,
        "unidentified": unidentified,
        "photos": photos_out,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--enroll-dir", required=True)
    parser.add_argument("--event-dir", required=True)
    parser.add_argument("--event-name", default="Local Test Event")
    parser.add_argument("--event-date", default="2026-09-21")
    parser.add_argument("--out", default="result.json")
    args = parser.parse_args()

    enroll_dir = Path(args.enroll_dir)
    event_dir = Path(args.event_dir)

    print("Enrolling members...")
    members_by_roll, ref_member_ids, ref_photo_names, ref_matrix = enroll_members(enroll_dir)
    print(f"Enrolled {len(set(ref_member_ids))} member(s) from {len(ref_member_ids)} accepted photo(s).")

    print("Processing event photos...")
    photos, per_photo_matches, all_unknown, faces_detected, faces_skipped = process_event(event_dir, ref_member_ids, ref_matrix)
    print(f"Processed {len(photos)} photo(s), {faces_detected} face(s) detected, {faces_skipped} skipped low quality.")

    result = build_result(args.event_name, args.event_date, members_by_roll, photos, per_photo_matches, all_unknown, faces_detected, faces_skipped)

    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote {args.out}")
    print(f"Summary: {result['summary']}")


if __name__ == "__main__":
    main()
