import pytest
import numpy as np
from app.verification.matcher import compute_cosine_similarity

def test_cosine_similarity_identical_vectors():
    """Identical vectors should yield a cosine similarity of 1.0."""
    v = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
    v_norm = v / np.linalg.norm(v)
    sim = compute_cosine_similarity(v_norm, v_norm)
    assert abs(sim - 1.0) < 1e-5


def test_cosine_similarity_orthogonal_vectors():
    """Orthogonal vectors should yield a cosine similarity of 0.0."""
    v1 = np.array([1.0, 0.0], dtype=np.float32)
    v2 = np.array([0.0, 1.0], dtype=np.float32)
    sim = compute_cosine_similarity(v1, v2)
    assert abs(sim - 0.0) < 1e-5
