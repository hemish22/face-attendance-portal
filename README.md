# Face Attendance Portal

Upload event photos, get back attendance per person (who's in which photos), unidentified-face clusters for strangers, a human review queue, and JSON/Excel exports. See `attendance-portal-build-spec.md` (in the parent directory) for the full spec.

## Status

- **M0-M2 (core pipeline + API):** done. `api/core/` (detection, quality gate, matching, clustering) has 17 passing pytest tests. The full FastAPI backend (auth, members, events, processing, review, clusters, export) is built and verified end-to-end.
- **M3 (web frontend):** done. Login, members (list/detail/enroll), events (list/create), and the full event detail page (Attendance/People/Photos/Review/Unidentified tabs, face overlay, keyboard-driven review queue).
- **M4 (hardening):** retention purge script (`api/scripts/purge.py`) done. Definition-of-done items around broader error-state polish are partial.
- **§13 threshold sweep:** not done in the full statistical sense — that needs 3-5 real past events with a `roll_no,present` ground-truth CSV from manual attendance sheets, which we don't have yet. Instead, the pipeline was validated on one real 12-photo group event: detection scales correctly to real 6000x3376 crowd photos, and a manual visual audit of a sample of matches (present, review-band, and unidentified) confirmed the default thresholds (`T_HIGH=0.50`, `T_LOW=0.35`) route correctly. Don't treat this as a substitute for the real sweep — re-run it once real ground truth is available.

## Local setup

```bash
# API
cd api && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m scripts.seed_admin
uvicorn app.main:app --reload --port 8000     # first run downloads buffalo_l (~300 MB)

# Web
cd web
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_URL to the API's URL
npm run dev
```

Regenerate API types after backend schema changes:
```bash
cd web && npx openapi-typescript http://localhost:8000/openapi.json -o src/lib/api-types.ts
```

## Tests

```bash
cd api && source .venv/bin/activate && python -m pytest tests/ -v
```

## Known deviations from the literal spec

- **DET_SIZE fallback.** InsightFace's SCRFD detector, at the spec's default `DET_SIZE=1280`, fails to detect a single large close-up face (e.g. a normal enrollment headshot) — its anchors aren't tuned for that scale and the score collapses to ~0. `core/detect.py` retries any pass (full-image or tile) that finds nothing at a smaller `FALLBACK_DET_SIZE=640`.
- **`unknown_clusters.rep_face_id` isn't a DB-level foreign key.** It and `faces.cluster_id` form a circular table dependency; SQLite tolerates the resulting creation order, Postgres (the spec's own deployment target) doesn't. The id is still a logical reference, just not FK-enforced.
- **shadcn/ui style.** The spec calls for "New York, Zinc" — the shadcn CLI has since dropped those preset names in favor of a `base-nova`/`neutral` default. Functionally equivalent (same neutral-gray family), just not exactly reproducible with current tooling.
- **Result JSON gained `photo_url`/`thumb_url`** on each `photos[]` entry (not in the original §9 JSON example) — the frontend needs an actual image URL to render the Photos tab and there wasn't one otherwise.
