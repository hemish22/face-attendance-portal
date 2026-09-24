import numpy as np

from app.config import settings
from core.match import match_faces


def unit(v):
    v = np.array(v, dtype=float)
    return v / np.linalg.norm(v)


def test_hungarian_never_assigns_one_member_to_two_faces():
    # Two members, two faces. Both faces are closest to member A, but the
    # Hungarian assignment must give each member at most one face per photo.
    ref_a = unit([1, 0])
    ref_b = unit([0, 1])
    ref_embeddings = np.array([ref_a, ref_b])
    ref_member_ids = ["A", "B"]

    face1 = unit([0.99, 0.10])  # closest to A
    face2 = unit([0.95, 0.30])  # also closest to A, but less so than face1
    faces = np.array([face1, face2])

    results = match_faces(faces, ref_embeddings, ref_member_ids)
    assigned_members = [r.member_id for r in results if r.member_id is not None]
    assert len(assigned_members) == len(set(assigned_members))


def test_classification_boundary_at_t_high():
    ref = unit([1, 0])
    theta = np.arccos(settings.T_HIGH)
    face = np.array([np.cos(theta), np.sin(theta)])  # dot product with ref == T_HIGH exactly

    results = match_faces(np.array([face]), np.array([ref]), ["A"])
    assert abs(results[0].score - settings.T_HIGH) < 1e-9
    assert results[0].status == "auto"


def test_classification_boundary_at_t_low():
    ref = unit([1, 0])
    theta = np.arccos(settings.T_LOW)
    face = np.array([np.cos(theta), np.sin(theta)])  # dot product with ref == T_LOW exactly

    results = match_faces(np.array([face]), np.array([ref]), ["A"])
    assert abs(results[0].score - settings.T_LOW) < 1e-9
    assert results[0].status == "review"


def test_classification_just_below_t_low_is_unknown():
    ref = unit([1, 0])
    theta = np.arccos(settings.T_LOW - 0.01)
    face = np.array([np.cos(theta), np.sin(theta)])

    results = match_faces(np.array([face]), np.array([ref]), ["A"])
    assert results[0].status == "unknown"
    assert results[0].member_id is None


def test_no_refs_gives_all_unknown():
    faces = np.array([unit([1, 0]), unit([0, 1])])
    results = match_faces(faces, np.zeros((0, 2)), [])
    assert all(r.status == "unknown" for r in results)


def test_no_faces_gives_empty():
    assert match_faces(np.zeros((0, 2)), np.array([unit([1, 0])]), ["A"]) == []
