import pytest

from games.orquantix.engine import (
    get_daily_word,
    get_difficulty,
    get_score,
    rank_map,
    progress,
)
from games.orquantix.vocabulary import compute_difficulty_thresholds
from tests.conftest import make_mock_model


# Reprises de l'ancien tests/test_game.py (Task 8 : app.py devient la coquille).
VOCAB_5 = ["maison", "chien", "arbre", "fleur", "chat"]
FREQ_5 = {"maison": 100.0, "chien": 80.0, "arbre": 60.0, "fleur": 40.0, "chat": 20.0}


def test_get_daily_word_returns_vocab_word():
    w = get_daily_word(VOCAB_5, 0)
    assert w in VOCAB_5


def test_get_daily_word_deterministic():
    assert get_daily_word(VOCAB_5, 0) == get_daily_word(VOCAB_5, 0)


def test_get_daily_word_different_index():
    results = {get_daily_word(VOCAB_5, i) for i in range(5)}
    assert len(results) >= 2


def test_get_difficulty_easy():
    thresholds = compute_difficulty_thresholds(VOCAB_5, FREQ_5)
    assert get_difficulty("maison", FREQ_5, thresholds) == 1


def test_get_difficulty_hard():
    thresholds = compute_difficulty_thresholds(VOCAB_5, FREQ_5)
    assert get_difficulty("chat", FREQ_5, thresholds) == 5


def test_get_difficulty_middle():
    thresholds = compute_difficulty_thresholds(VOCAB_5, FREQ_5)
    d = get_difficulty("arbre", FREQ_5, thresholds)
    assert 1 <= d <= 5


def test_get_score_exact_word():
    model = make_mock_model(["chien", "chat"])
    score = get_score(model, "chien", "chien")
    assert score == 100.0


def test_get_score_range():
    model = make_mock_model(["chien", "chat", "maison"])
    score = get_score(model, "chat", "chien")
    assert 0.0 <= score <= 100.0


def test_get_score_two_decimals():
    model = make_mock_model(["chien", "chat"])
    score = get_score(model, "chat", "chien")
    assert round(score, 2) == score


def test_rank_map_structure():
    # neighbours tel que le rend model.most_similar : le mot cible n'y
    # figure jamais, donc rank_map n'a pas à l'exclure lui-même.
    neighbours = [("b", 0.9), ("c", 0.7), ("d", 0.5), ("e", 0.3)]
    top = rank_map(neighbours)
    assert isinstance(top, dict)
    assert "a" not in top
    assert all(isinstance(v, int) for v in top.values())
    assert min(top.values()) == 1


def test_rank_map_ranks_contiguous():
    neighbours = [("b", 0.9), ("c", 0.7), ("d", 0.5), ("e", 0.3)]
    top = rank_map(neighbours)
    ranks = sorted(top.values())
    assert ranks == list(range(1, len(ranks) + 1))


def test_progress_is_zero_outside_the_top_1000():
    assert progress(None) == 0.0
    assert progress(1001) == 0.0
    assert progress(15000) == 0.0


def test_progress_is_100_only_when_found():
    assert progress(500, found=True) == 100.0
    assert progress(1) < 100.0


def test_progress_matches_the_original_curve():
    # Valeurs de reference de la courbe ((1001-rang)/1000)^3.4 * 100.
    assert progress(1) == 99.99
    assert progress(10) == 96.97
    assert progress(50) == 84.30
    assert progress(100) == 70.16
    assert progress(300) == 29.88
    assert progress(400) == 17.71
    assert progress(1000) == 0.0


def test_progress_stays_near_zero_in_the_far_half_of_the_neighbourhood():
    # C'est la raison d'etre de cette courbe : un voisin de rang 800
    # n'apprend rien au joueur, la barre doit rester quasi vide.
    assert progress(600) < 5
    assert progress(800) < 1
    assert progress(800) > 0


def test_progress_is_monotonic():
    values = [progress(r) for r in [1000, 800, 600, 400, 300, 100, 50, 10, 1]]

    assert values == sorted(values)
