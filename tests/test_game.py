import pytest
from tests.conftest import make_mock_model, MODEL_VOCAB
from games.orquantix.vocabulary import compute_difficulty_thresholds


VOCAB_5 = ["maison", "chien", "arbre", "fleur", "chat"]
FREQ_5 = {"maison": 100.0, "chien": 80.0, "arbre": 60.0, "fleur": 40.0, "chat": 20.0}


def test_get_daily_word_returns_vocab_word():
    from games.orquantix.engine import get_daily_word
    w = get_daily_word(VOCAB_5, 0)
    assert w in VOCAB_5


def test_get_daily_word_deterministic():
    from games.orquantix.engine import get_daily_word
    assert get_daily_word(VOCAB_5, 0) == get_daily_word(VOCAB_5, 0)


def test_get_daily_word_different_index():
    from games.orquantix.engine import get_daily_word
    results = {get_daily_word(VOCAB_5, i) for i in range(5)}
    assert len(results) >= 2


def test_get_difficulty_easy():
    from games.orquantix.engine import get_difficulty
    thresholds = compute_difficulty_thresholds(VOCAB_5, FREQ_5)
    assert get_difficulty("maison", FREQ_5, thresholds) == 1


def test_get_difficulty_hard():
    from games.orquantix.engine import get_difficulty
    thresholds = compute_difficulty_thresholds(VOCAB_5, FREQ_5)
    assert get_difficulty("chat", FREQ_5, thresholds) == 5


def test_get_difficulty_middle():
    from games.orquantix.engine import get_difficulty
    thresholds = compute_difficulty_thresholds(VOCAB_5, FREQ_5)
    d = get_difficulty("arbre", FREQ_5, thresholds)
    assert 1 <= d <= 5


def test_get_score_exact_word():
    from games.orquantix.engine import get_score
    model = make_mock_model(["chien", "chat"])
    score = get_score(model, "chien", "chien")
    assert score == 100.0


def test_get_score_range():
    from games.orquantix.engine import get_score
    model = make_mock_model(["chien", "chat", "maison"])
    score = get_score(model, "chat", "chien")
    assert 0.0 <= score <= 100.0


def test_get_score_two_decimals():
    from games.orquantix.engine import get_score
    model = make_mock_model(["chien", "chat"])
    score = get_score(model, "chat", "chien")
    assert round(score, 2) == score


def test_get_top1000_structure():
    from games.orquantix.engine import get_top1000
    words = ["a", "b", "c", "d", "e"]
    model = make_mock_model(words)
    top = get_top1000(model, "a")
    assert isinstance(top, dict)
    assert "a" not in top
    assert all(isinstance(v, int) for v in top.values())
    assert min(top.values()) == 1


def test_get_top1000_ranks_contiguous():
    from games.orquantix.engine import get_top1000
    words = ["a", "b", "c", "d", "e"]
    model = make_mock_model(words)
    top = get_top1000(model, "a")
    ranks = sorted(top.values())
    assert ranks == list(range(1, len(ranks) + 1))


def test_get_better_hint_word_returns_closer_unused_candidate():
    from games.orquantix.engine import get_better_hint_word

    top1000 = {"a": 900, "b": 700, "c": 500, "d": 250}
    hinted = get_better_hint_word(top1000, 700, guessed_words={"c"})
    assert hinted == "d"


def test_get_better_hint_word_returns_none_for_best_rank():
    from games.orquantix.engine import get_better_hint_word

    assert get_better_hint_word({"a": 1}, 1) is None


def test_get_strong_hint_word_prefers_top_rank():
    from games.orquantix.engine import get_strong_hint_word

    top1000 = {"a": 80, "b": 12, "c": 4}
    assert get_strong_hint_word(top1000, guessed_words={"c"}) == "b"
