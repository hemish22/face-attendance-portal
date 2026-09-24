"""Per-photo face-to-member matching via Hungarian assignment. Pure Python."""

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.config import settings


@dataclass
class Candidate:
    member_id: str
    score: float


@dataclass
class MatchResult:
    face_index: int
    status: str  # "auto" | "review" | "unknown"
    member_id: str | None
    score: float | None
    candidates: list[Candidate] = field(default_factory=list)


def match_faces(
    face_embeddings: np.ndarray,  # (F, 512)
    ref_embeddings: np.ndarray,  # (R, 512)
    ref_member_ids: list[str],  # length R, member id owning each ref
) -> list[MatchResult]:
    """Runs per photo, using only that photo's non-skipped faces."""
    n_faces = face_embeddings.shape[0]

    if n_faces == 0:
        return []

    if ref_embeddings.shape[0] == 0:
        return [MatchResult(face_index=i, status="unknown", member_id=None, score=None) for i in range(n_faces)]

    member_ids = sorted(set(ref_member_ids))
    member_index = {m: i for i, m in enumerate(member_ids)}
    n_members = len(member_ids)

    similarity = face_embeddings @ ref_embeddings.T  # (F, R)

    scores_by_member = np.full((n_faces, n_members), -1.0)
    for r, member_id in enumerate(ref_member_ids):
        m = member_index[member_id]
        scores_by_member[:, m] = np.maximum(scores_by_member[:, m], similarity[:, r])

    rows, cols = linear_sum_assignment(-scores_by_member)
    assigned_member_by_row = {row: col for row, col in zip(rows, cols)}

    results: list[MatchResult] = []
    for i in range(n_faces):
        top3_idx = np.argsort(-scores_by_member[i])[:3]
        candidates = [
            Candidate(member_id=member_ids[idx], score=float(scores_by_member[i, idx]))
            for idx in top3_idx
            if scores_by_member[i, idx] > -1.0
        ]

        if i not in assigned_member_by_row:
            results.append(MatchResult(face_index=i, status="unknown", member_id=None, score=None, candidates=candidates))
            continue

        m = assigned_member_by_row[i]
        s = float(scores_by_member[i, m])
        if s >= settings.T_HIGH:
            status = "auto"
        elif s >= settings.T_LOW:
            status = "review"
        else:
            status = "unknown"

        member_id = member_ids[m] if status != "unknown" else None
        results.append(MatchResult(face_index=i, status=status, member_id=member_id, score=s, candidates=candidates))

    return results
