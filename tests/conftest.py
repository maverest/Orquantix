import numpy as np
import pytest
from gensim.models import KeyedVectors

# Minimal Lexique383 TSV for tests.
# Columns used: 1_ortho, 3_lemme, 4_cgram, 5_genre, 6_nombre, 7_freqlemlivres
LEXIQUE_TSV = (
    "1_ortho\t3_lemme\t4_cgram\t5_genre\t6_nombre\t7_freqlemlivres\n"
    "chien\tchien\tNOM\tm\ts\t52.3\n"
    "chienne\tchien\tNOM\tf\ts\t18.7\n"
    "chiens\tchien\tNOM\tm\tp\t30.2\n"
    "beau\tbeau\tADJ\tm\ts\t120.5\n"
    "belle\tbeau\tADJ\tf\ts\t95.3\n"
    "beaux\tbeau\tADJ\tm\tp\t40.2\n"
    "manger\tmanger\tVER\t\t\t65.0\n"
    "mangeons\tmanger\tVER\t\t\t12.1\n"
    "chat\tchat\tNOM\tm\ts\t45.0\n"
    "fleur\tfleur\tNOM\tf\ts\t38.0\n"
    "brun\tbrun\tADJ\tm\ts\t22.0\n"
    "courir\tcourir\tVER\t\t\t18.0\n"
    "absent\tabsent\tNOM\tm\ts\t10.0\n"
)

# Model vocab: all words above EXCEPT "absent"
MODEL_VOCAB = ["chien", "chienne", "chiens", "beau", "belle", "beaux",
               "manger", "mangeons", "chat", "fleur", "brun", "courir"]


def make_mock_model(words: list[str], vector_size: int = 10) -> KeyedVectors:
    """Create a deterministic KeyedVectors for testing."""
    rng = np.random.default_rng(42)
    vectors = rng.random((len(words), vector_size)).astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms
    kv = KeyedVectors(vector_size=vector_size)
    kv.add_vectors(words, vectors)
    return kv


@pytest.fixture
def mock_model():
    return make_mock_model(MODEL_VOCAB)


@pytest.fixture
def lexique_file(tmp_path):
    p = tmp_path / "Lexique383.tsv"
    p.write_text(LEXIQUE_TSV, encoding="utf-8")
    return str(p)
