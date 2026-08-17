import numpy as np
from gensim.models import KeyedVectors


def make_mock_model(words: list[str], vector_size: int = 10) -> KeyedVectors:
    """Create a deterministic KeyedVectors for testing."""
    rng = np.random.default_rng(42)
    vectors = rng.random((len(words), vector_size)).astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms
    kv = KeyedVectors(vector_size=vector_size)
    kv.add_vectors(words, vectors)
    return kv
