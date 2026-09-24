import numpy as np

from core.cluster import cluster_faces, representative_index


def unit(v):
    v = np.array(v, dtype=float)
    return v / np.linalg.norm(v)


def test_single_face_gets_one_cluster():
    labels = cluster_faces(np.array([unit([1, 0, 0])]))
    assert list(labels) == [0]


def test_empty_input_gives_empty_output():
    labels = cluster_faces(np.zeros((0, 3)))
    assert len(labels) == 0


def test_clusters_synthetic_groups_correctly():
    # Two tight groups of near-identical embeddings, far apart from each other.
    rng = np.random.default_rng(0)
    center_a = unit([1, 0, 0, 0])
    center_b = unit([0, 1, 0, 0])

    def jittered(center, n):
        pts = [unit(center + rng.normal(scale=0.01, size=4)) for _ in range(n)]
        return pts

    group_a = jittered(center_a, 4)
    group_b = jittered(center_b, 3)
    embeddings = np.array(group_a + group_b)

    labels = cluster_faces(embeddings)

    labels_a = set(labels[:4])
    labels_b = set(labels[4:])
    assert len(labels_a) == 1
    assert len(labels_b) == 1
    assert labels_a != labels_b


def test_representative_index_picks_highest_score_times_width():
    det_scores = np.array([0.9, 0.5, 0.99])
    widths = np.array([50, 200, 100])
    # products: 45, 100, 99 -> index 1 wins
    assert representative_index(det_scores, widths) == 1
