import pytest
from tests.conftest import make_mock_model, MODEL_VOCAB
from vocabulary import build_norm_map, compute_difficulty_thresholds
from game import get_top1000
from app import AppState, create_app


VOCAB = ["chien", "chat", "maison", "arbre", "fleur"]
FREQ = {"chien": 52.3, "chat": 45.0, "maison": 80.0, "arbre": 30.0, "fleur": 15.0}


@pytest.fixture
def model():
    return make_mock_model(VOCAB)


@pytest.fixture
def ready_state(model):
    state = AppState()
    thresholds = compute_difficulty_thresholds(VOCAB, FREQ)
    state.phase = "ready"
    state.progress = 100
    state.detail = "Prêt !"
    state.model = model
    state.vocab = VOCAB
    state.freq_by_word = FREQ
    state.norm_to_vocab = build_norm_map(VOCAB)
    state.norm_to_model = build_norm_map(VOCAB)
    state.difficulty_thresholds = thresholds
    state.top1000 = get_top1000(model, "chien")
    state.daily_word = "chien"
    state.daily_difficulty = 2
    state.game_index = 0
    return state


@pytest.fixture
def client(ready_state):
    app = create_app(ready_state)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_status_ready(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["phase"] == "ready"
    assert data["progress"] == 100


def test_status_downloading():
    state = AppState()
    state.phase = "downloading"
    state.progress = 42
    state.detail = "Test detail"
    app = create_app(state)
    app.config["TESTING"] = True
    with app.test_client() as c:
        resp = c.get("/status")
        data = resp.get_json()
        assert data["phase"] == "downloading"
        assert data["progress"] == 42
        assert data["detail"] == "Test detail"


def test_daily_info(client, ready_state):
    resp = client.get("/daily-info")
    data = resp.get_json()
    assert data["difficulty"] == ready_state.daily_difficulty
    assert data["word_length"] == len(ready_state.daily_word)


def test_guess_win(client):
    resp = client.post("/guess", json={"word": "chien"})
    data = resp.get_json()
    assert data["win"] is True
    assert data["score"] == 100.0
    assert data["word"] == "chien"
    assert data["gave_up"] is False
    assert data["proximity"]["progress"] == 100.0
    assert data["proximity"]["mood"] == "found"


def test_guess_win_normalized(client):
    resp = client.post("/guess", json={"word": "CHIEN"})
    data = resp.get_json()
    assert data["win"] is True


def test_guess_known_word(client):
    resp = client.post("/guess", json={"word": "chat"})
    data = resp.get_json()
    assert data["word"] == "chat"
    assert "score" in data
    assert 0.0 <= data["score"] <= 100.0
    assert data["win"] is False
    assert "proximity" in data
    assert "progress" in data["proximity"]
    assert "mood" in data["proximity"]
    assert "emoji" in data["proximity"]
    assert data["proximity"]["progress"] < 100.0


def test_guess_unknown_word(client):
    resp = client.post("/guess", json={"word": "xyznotaword"})
    data = resp.get_json()
    assert "error" in data
    assert "score" not in data


def test_guess_missing_field(client):
    resp = client.post("/guess", json={})
    assert resp.status_code == 400


def test_give_up_reveals_daily_word(client, ready_state):
    resp = client.post("/give-up")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["word"] == ready_state.daily_word
    assert data["win"] is True
    assert data["gave_up"] is True
    assert data["proximity"]["mood"] == "found"


def test_new_game_increments_index(client, ready_state):
    resp = client.post("/new-game")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "difficulty" in data
    assert "word_length" in data
    assert ready_state.game_index == 1


def test_new_game_recomputes_top1000(client, ready_state):
    client.post("/new-game")
    assert ready_state.game_index == 1


def test_suggest_finds_close_word(client, ready_state):
    # "chein" est une faute de frappe de "chien" (dans le vocab du modèle)
    resp = client.post("/suggest", json={"word": "chein"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["suggestion"] == "chien"


def test_suggest_returns_null_when_no_match(client, ready_state):
    # "xqzjkl" n'a aucun proche dans le petit vocab de test
    resp = client.post("/suggest", json={"word": "xqzjkl"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["suggestion"] is None


def test_suggest_missing_field(client):
    resp = client.post("/suggest", json={})
    assert resp.status_code == 400


def test_hint_first_letter(client, ready_state):
    resp = client.post("/hint", json={"type": "first-letter"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["value"] == ready_state.daily_word[0]


def test_hint_word_length(client, ready_state):
    resp = client.post("/hint", json={"type": "word-length"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["value"] == len(ready_state.daily_word)
    assert "lettres" in data["message"]


def test_hint_better_word(client, ready_state):
    worst_rank = max(ready_state.top1000.values())
    guessed_word = next(word for word, rank in ready_state.top1000.items() if rank == worst_rank)
    resp = client.post("/hint", json={
        "type": "better-word",
        "best_rank": worst_rank,
        "guessed_words": [guessed_word],
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["value"] in ready_state.top1000
    assert ready_state.top1000[data["value"]] < worst_rank
    assert data["value"] != guessed_word


def test_hint_golden_fish_returns_strong_neighbor(client, ready_state):
    resp = client.post("/hint", json={
        "type": "golden-fish",
        "guessed_words": [],
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["value"] in ready_state.top1000
    assert ready_state.top1000[data["value"]] <= 100


def test_suggest_not_ready():
    state = AppState()
    state.phase = "loading"
    app = create_app(state)
    app.config["TESTING"] = True
    with app.test_client() as c:
        resp = c.post("/suggest", json={"word": "chien"})
        assert resp.status_code == 503
