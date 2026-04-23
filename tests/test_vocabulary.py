import pytest
from tests.conftest import LEXIQUE_TSV, MODEL_VOCAB, make_mock_model
from vocabulary import (
    normalize,
    build_norm_map,
    filter_eligible_words,
    compute_difficulty_thresholds,
)


def test_normalize_lowercase():
    assert normalize("CHIEN") == "chien"


def test_normalize_accents():
    assert normalize("Église") == "eglise"
    assert normalize("naïf") == "naif"
    assert normalize("cœur") == "coeur"


def test_build_norm_map_maps_original():
    words = ["église", "naïf", "chien"]
    m = build_norm_map(words)
    assert m["eglise"] == "église"
    assert m["naif"] == "naïf"
    assert m["chien"] == "chien"


def test_filter_nouns_singular(lexique_file):
    model_vocab = set(MODEL_VOCAB)
    vocab, _ = filter_eligible_words(lexique_file, model_vocab)
    assert "chien" in vocab
    assert "chat" in vocab
    assert "chienne" in vocab
    assert "chiens" not in vocab


def test_filter_adj_masculin_singulier(lexique_file):
    model_vocab = set(MODEL_VOCAB)
    vocab, _ = filter_eligible_words(lexique_file, model_vocab)
    assert "beau" in vocab
    assert "belle" not in vocab
    assert "beaux" not in vocab


def test_filter_verb_infinitif(lexique_file):
    model_vocab = set(MODEL_VOCAB)
    vocab, _ = filter_eligible_words(lexique_file, model_vocab)
    assert "manger" in vocab
    assert "mangeons" not in vocab


def test_filter_excludes_word_not_in_model(lexique_file):
    model_vocab = set(MODEL_VOCAB)
    vocab, _ = filter_eligible_words(lexique_file, model_vocab)
    assert "absent" not in vocab


def test_filter_returns_freq_by_word(lexique_file):
    model_vocab = set(MODEL_VOCAB)
    vocab, freq = filter_eligible_words(lexique_file, model_vocab)
    assert "chien" in freq
    assert freq["chien"] == pytest.approx(52.3)


def test_compute_difficulty_thresholds_length():
    vocab = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
    freq = {w: float(i + 1) * 10 for i, w in enumerate(vocab)}
    t = compute_difficulty_thresholds(vocab, freq)
    assert len(t) == 4


def test_compute_difficulty_thresholds_ascending():
    vocab = ["a", "b", "c", "d", "e"]
    freq = {"a": 100.0, "b": 80.0, "c": 60.0, "d": 40.0, "e": 20.0}
    t = compute_difficulty_thresholds(vocab, freq)
    assert t == sorted(t)
