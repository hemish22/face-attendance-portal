"""Threshold sweep per build-spec §13.

Detects+embeds every event photo ONCE (expensive), caches it, then sweeps
T_HIGH from 0.35 to 0.65 in steps of 0.05 (T_LOW = T_HIGH - 0.15) re-running
only the cheap matching step per threshold.

Without a roll_no,present ground-truth CSV this can't compute real
precision/recall (§13's actual target metrics) — it reports review rate and
match-score distribution instead, which is what's honestly available from
detection-only data. Pass --ground-truth to get the real metrics.

Usage:
    python -m scripts.sweep --enroll-dir <dir> --event-dir <dir> [--ground-truth roll_no_present.csv] [--cache cache.pkl]
"""

import argparse
import csv
import pickle
from pathlib import Path

import numpy as np

from core.match import match_faces
from scripts.run_event import enroll_members, glob_images, load_exif_corrected_bgr
from core.detect import detect_faces

T_HIGH_VALUES = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65]
T_LOW_OFFSET = 0.15


def build_cache(enroll_dir: Path, event_dir: Path, cache_path: Path):
    print("Enrolling members...")
    members_by_roll, ref_member_ids, _, ref_matrix = enroll_members(enroll_dir)
    print(f"Enrolled {len(set(ref_member_ids))} member(s).")

    print("Detecting faces in event photos (this is the slow part, run once)...")
    photo_paths = glob_images(event_dir)
    per_photo = []  # list of (filename, [DetectedFace, ...] usable only)
    total_faces = 0
    total_skipped = 0
    for i, path in enumerate(photo_paths):
        image = load_exif_corrected_bgr(path)
        detected = detect_faces(image)
        usable = [f for f in detected if not f.skipped]
        total_faces += len(detected)
        total_skipped += len(detected) - len(usable)
        per_photo.append((path.name, [(f.embedding, f.det_score, f.bbox) for f in usable]))
        print(f"  [{i+1}/{len(photo_paths)}] {path.name}: {len(detected)} detected, {len(usable)} usable")

    cache = {
        "members_by_roll": members_by_roll,
        "ref_member_ids": ref_member_ids,
        "ref_matrix": ref_matrix,
        "per_photo": per_photo,
        "total_faces": total_faces,
        "total_skipped": total_skipped,
    }
    with open(cache_path, "wb") as f:
        pickle.dump(cache, f)
    print(f"Cached to {cache_path}")
    return cache


def sweep_thresholds(cache: dict, ground_truth: dict[str, bool] | None):
    import app.config as config_module

    members_by_roll = cache["members_by_roll"]
    ref_member_ids = cache["ref_member_ids"]
    ref_matrix = cache["ref_matrix"]
    per_photo = cache["per_photo"]

    print(f"\n{len(members_by_roll)} members, {len(per_photo)} photos, "
          f"{cache['total_faces']} faces detected ({cache['total_skipped']} skipped low quality)\n")

    header = f"{'T_HIGH':>7} {'T_LOW':>7} {'present':>8} {'review':>7} {'unknown_faces':>14} {'review_rate':>12}"
    if ground_truth:
        header += f" {'precision':>10} {'recall':>8}"
    print(header)

    for t_high in T_HIGH_VALUES:
        t_low = round(t_high - T_LOW_OFFSET, 2)
        config_module.settings.T_HIGH = t_high
        config_module.settings.T_LOW = t_low

        present_members = set()
        review_members = set()
        unknown_face_count = 0

        for _filename, faces in per_photo:
            if not faces:
                continue
            embeddings = np.array([f[0] for f in faces])
            matches = match_faces(embeddings, ref_matrix, ref_member_ids)
            for m in matches:
                if m.status == "auto":
                    present_members.add(m.member_id)
                elif m.status == "review":
                    review_members.add(m.member_id)
                else:
                    unknown_face_count += 1

        review_members -= present_members
        review_rate = len(review_members) / len(members_by_roll) if members_by_roll else 0

        row = f"{t_high:>7.2f} {t_low:>7.2f} {len(present_members):>8} {len(review_members):>7} {unknown_face_count:>14} {review_rate:>11.1%}"

        if ground_truth:
            tp = sum(1 for m in present_members if ground_truth.get(m))
            fp = sum(1 for m in present_members if not ground_truth.get(m, False))
            actual_present = sum(1 for v in ground_truth.values() if v)
            precision = tp / len(present_members) if present_members else 0
            recall = tp / actual_present if actual_present else 0
            row += f" {precision:>9.1%} {recall:>7.1%}"

        print(row)


def load_ground_truth(path: Path) -> dict[str, bool]:
    out = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            out[row["roll_no"]] = row["present"].strip().lower() in ("1", "true", "yes", "present")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--enroll-dir", required=True)
    parser.add_argument("--event-dir", required=True)
    parser.add_argument("--ground-truth", default=None, help="CSV with roll_no,present columns")
    parser.add_argument("--cache", default="/tmp/sweep_cache.pkl")
    parser.add_argument("--use-cache", action="store_true", help="Skip detection, reuse an existing cache file")
    args = parser.parse_args()

    cache_path = Path(args.cache)
    if args.use_cache and cache_path.exists():
        print(f"Loading cached detections from {cache_path}")
        with open(cache_path, "rb") as f:
            cache = pickle.load(f)
    else:
        cache = build_cache(Path(args.enroll_dir), Path(args.event_dir), cache_path)

    ground_truth = load_ground_truth(Path(args.ground_truth)) if args.ground_truth else None
    if not ground_truth:
        print("\nNo --ground-truth CSV given: reporting review rate and match counts only, "
              "not real precision/recall. Pass --ground-truth roll_no_present.csv for the §13 metrics.")

    sweep_thresholds(cache, ground_truth)


if __name__ == "__main__":
    main()
