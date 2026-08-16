import pytest

from games.orquantix.engine import (
    TemperatureScale,
    build_temperature_scale,
    get_daily_word,
    get_difficulty,
    get_score,
    get_top1000,
    temperature,
)
from games.orquantix.vocabulary import compute_difficulty_thresholds
from tests.conftest import make_mock_model

# Ancres réelles mesurées sur la cible "confiture".
SCALE = TemperatureScale(floor=0.0391, top1000=0.1551, maximum=0.7113)

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


def test_get_top1000_structure():
    words = ["a", "b", "c", "d", "e"]
    model = make_mock_model(words)
    top = get_top1000(model, "a")
    assert isinstance(top, dict)
    assert "a" not in top
    assert all(isinstance(v, int) for v in top.values())
    assert min(top.values()) == 1


def test_get_top1000_ranks_contiguous():
    words = ["a", "b", "c", "d", "e"]
    model = make_mock_model(words)
    top = get_top1000(model, "a")
    ranks = sorted(top.values())
    assert ranks == list(range(1, len(ranks) + 1))


def test_temperature_is_zero_at_and_below_the_floor():
    assert temperature(SCALE, 0.0391) == 0.0
    assert temperature(SCALE, 0.0) == 0.0
    assert temperature(SCALE, -0.05) == 0.0


def test_temperature_is_fifty_at_the_top1000_threshold():
    # 50° signifie exactement « je viens d'entrer dans le top 1000 ».
    assert temperature(SCALE, 0.1551) == pytest.approx(50.0, abs=0.05)


def test_temperature_caps_at_99_for_the_closest_neighbour():
    # 100 est réservé à la victoire.
    assert temperature(SCALE, 0.7113) == pytest.approx(99.0, abs=0.05)


def test_temperature_is_100_only_when_found():
    assert temperature(SCALE, 0.5, found=True) == 100.0


def test_temperature_matches_measured_values():
    # Valeurs vérifiées sur le vrai modèle, cible "confiture".
    assert round(temperature(SCALE, 0.680)) == 96   # compote, rang 2
    assert round(temperature(SCALE, 0.452)) == 76   # tartine, rang 78
    assert round(temperature(SCALE, 0.316)) == 64   # cuisine, rang 290
    assert round(temperature(SCALE, 0.072)) == 14   # bonjour, hors top 1000
    assert round(temperature(SCALE, 0.038)) == 0    # moteur, hors top 1000


def test_temperature_separates_two_words_that_used_to_both_read_zero():
    # Le cas qui justifie toute la refonte.
    bonjour = temperature(SCALE, 0.072)
    moteur = temperature(SCALE, 0.038)

    assert bonjour > moteur
    assert bonjour > 10


def test_temperature_is_monotonic():
    values = [temperature(SCALE, c) for c in [0.0, 0.05, 0.10, 0.155, 0.3, 0.5, 0.7113]]

    assert values == sorted(values)


def test_build_scale_uses_first_and_thousandth_neighbour():
    neighbours = [(f"w{i}", 1.0 - i / 1000) for i in range(1000)]

    scale = build_temperature_scale(_FakeModel(), "cible", neighbours)

    assert scale.maximum == pytest.approx(1.0)
    assert scale.top1000 == pytest.approx(1.0 - 999 / 1000)


def test_build_scale_handles_short_neighbour_lists():
    neighbours = [("a", 0.8), ("b", 0.4)]

    scale = build_temperature_scale(_FakeModel(), "cible", neighbours)

    assert scale.maximum == pytest.approx(0.8)
    assert scale.top1000 == pytest.approx(0.4)
    assert scale.floor < scale.top1000


def test_build_scale_with_single_neighbour():
    """Garde-fou : top1000 == maximum doit être corrigé."""
    neighbours = [("w0", 0.8)]

    scale = build_temperature_scale(_FakeModel(), "cible", neighbours)

    # Les trois ancres doivent être strictement croissantes.
    assert scale.floor < scale.top1000 < scale.maximum


def test_build_scale_guards_do_not_violate_each_other():
    """Contre-exemple : deuxième garde-fou invalide le premier.

    Entrées : floor=0.9, top1000=1.0, maximum=1.0
    - Première garde : 0.9 < 1.0 → pas d'action
    - Deuxième garde : 1.0 >= 1.0 → top1000 = 0.5
    - Résultat : floor=0.9 > top1000=0.5 → invariant violé
    """
    neighbours = [("w0", 1.0)]
    model = _FakeModelWithMedian(median=0.9)

    scale = build_temperature_scale(model, "cible", neighbours)

    # Les trois ancres doivent rester strictement croissantes.
    assert scale.floor < scale.top1000, f"floor={scale.floor} should be < top1000={scale.top1000}"
    assert scale.top1000 < scale.maximum, f"top1000={scale.top1000} should be < maximum={scale.maximum}"


def test_temperature_is_monotonic_on_degenerate_scale():
    """Un échelle dégénérée qui a passé les garde-fou reste utilisable."""
    neighbours = [("w0", 1.0)]
    model = _FakeModelWithMedian(median=0.9)

    scale = build_temperature_scale(model, "cible", neighbours)

    # temperature() doit retourner des valeurs croissantes monotoniquement.
    values = [temperature(scale, c) for c in [0.0, 0.5, 0.8, 0.99, 1.0]]
    assert values == sorted(values), f"Values {values} are not monotonic"


class _FakeModel:
    """Modèle minimal : expose seulement ce que build_temperature_scale lit."""

    def __init__(self) -> None:
        self.key_to_index = {f"w{i}": i for i in range(1000)}
        self.key_to_index["cible"] = 0

    def similarity(self, a: str, b: str) -> float:
        return 0.02

    def get_normed_vectors(self):
        import numpy as np
        return np.full((1000, 4), 0.02, dtype=np.float32)


class _FakeModelWithMedian(_FakeModel):
    """Modèle fake qui retourne une médiane spécifique via dot product."""

    def __init__(self, median: float) -> None:
        super().__init__()
        self.median = median

    def get_normed_vectors(self):
        import numpy as np
        # Vectors where dot product gives the desired median similarity.
        # If v = [sqrt(median), 0, 0, 0], then v @ v = median.
        vecs = np.zeros((1001, 4), dtype=np.float32)
        vecs[:, 0] = np.sqrt(self.median)
        return vecs
