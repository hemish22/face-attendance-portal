"""Unknown-face clustering. Pure Python — no FastAPI or DB imports."""

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from app.config import settings


def cluster_faces(embeddings: np.ndarray) -> np.ndarray:
    """Clusters embeddings (N, 512) into groups of the same stranger.

    Over-splits rather than over-merges: one person in two labels costs one
    Merge click, two people merged into one is a wrong record. Returns an
    (N,) array of integer cluster ids (0..k-1), one per input face.
    """
    n = embeddings.shape[0]
    if n == 0:
        return np.array([], dtype=int)
    if n == 1:
        return np.array([0])

    model = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=1 - settings.T_CLUSTER,
    )
    return model.fit_predict(embeddings)


def assign_to_existing_or_new(
    new_embeddings: np.ndarray,  # (N, 512)
    existing_cluster_ids: list[str],
    existing_centroids: np.ndarray,  # (K, 512), rows aligned to existing_cluster_ids
) -> list[str | int]:
    """Incremental clustering for new uploads.

    Resolved (assigned/merged/dismissed) clusters are frozen: a new unknown
    face joins the nearest existing cluster if its similarity to that
    cluster's centroid is >= T_CLUSTER, otherwise it forms a new cluster with
    other new faces that also didn't match. Returns one entry per new face:
    either an existing cluster id (str) or a temporary int label (0..k-1) for
    a newly formed cluster among the leftovers.
    """
    n = new_embeddings.shape[0]
    assignments: list[str | int] = [None] * n  # type: ignore[list-item]
    leftover_indices = []

    if existing_centroids.shape[0] > 0:
        similarity = new_embeddings @ existing_centroids.T  # (N, K)
        best_idx = np.argmax(similarity, axis=1)
        best_score = similarity[np.arange(n), best_idx]
        for i in range(n):
            if best_score[i] >= settings.T_CLUSTER:
                assignments[i] = existing_cluster_ids[best_idx[i]]
            else:
                leftover_indices.append(i)
    else:
        leftover_indices = list(range(n))

    if leftover_indices:
        leftover_embeddings = new_embeddings[leftover_indices]
        labels = cluster_faces(leftover_embeddings)
        for local_i, face_i in enumerate(leftover_indices):
            assignments[face_i] = int(labels[local_i])

    return assignments


def representative_index(det_scores: np.ndarray, widths: np.ndarray) -> int:
    """The rep crop is the face with the highest det_score x width."""
    return int(np.argmax(det_scores * widths))


def order_clusters(cluster_face_counts: dict, first_seen: dict) -> list:
    """Numbers clusters by appearance count descending, then by first photo.

    cluster_face_counts: {cluster_key: appearance_count}
    first_seen: {cluster_key: sortable value, e.g. earliest photo index}
    Returns cluster_keys in display order (index 0 -> "Unidentified Person 1").
    """
    return sorted(cluster_face_counts.keys(), key=lambda k: (-cluster_face_counts[k], first_seen[k]))
