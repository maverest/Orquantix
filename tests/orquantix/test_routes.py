import pytest
from flask import Flask

from games.orquantix.engine import TemperatureScale, get_top1000, get_neighbours
from games.orquantix.routes import build_blueprint
from games.orquantix.state import OrquantixState
from games.orquantix.vocabulary import Pools, build_norm_map
from tests.conftest import make_mock_model

VOCAB = ["chien", "chat", "maison", "arbre", "fleur"]


@pytest.fixture
def state():
    model = make_mock_model(VOCAB)
    s = OrquantixState()
    s.phase = "ready"
    s.model = model
    s.pools = Pools(
        mystery_words=VOCAB,
        mystery_freq={w: 50.0 for w in VOCAB},
        hint_words=frozenset(VOCAB),
    )
    s.norm_to_model = build_norm_map(VOCAB)
    s.neighbours = get_neighbours(model, "chien", topn=4)
    s.top1000 = get_top1000(model, "chien")
    s.scale = TemperatureScale(floor=0.0, top1000=0.2, maximum=0.9)
    s.mystery_word = "chien"
    s.difficulty = 2
    s.littre = None
    return s


@pytest.fixture
def client(state):
    app = Flask(__name__)
    app.register_blueprint(build_blueprint(state))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_routes_are_namespaced_under_the_game(client):
    # Le préfixe évite la collision quand un quiz voudra son propre /guess.
    assert client.post("/games/orquantix/guess", json={"word": "chat"}).status_code == 200
    assert client.post("/guess", json={"word": "chat"}).status_code == 404


def test_guess_returns_temperature_and_rank(client):
    data = client.post("/games/orquantix/guess", json={"word": "chat"}).get_json()

    assert "temperature" in data
    assert "rank" in data
    assert "mood" in data
    assert data["win"] is False


def test_guess_the_mystery_word_wins_at_100_degrees(client):
    data = client.post("/games/orquantix/guess", json={"word": "chien"}).get_json()

    assert data["win"] is True
    assert data["temperature"] == 100.0
    assert data["mood"] == "found"


def test_guess_is_accent_and_case_insensitive(client):
    data = client.post("/games/orquantix/guess", json={"word": "CHIEN"}).get_json()

    assert data["win"] is True


def test_unknown_word_is_rejected(client):
    data = client.post("/games/orquantix/guess", json={"word": "zzzzz"}).get_json()

    assert data["error"] == "inconnu"


def test_give_up_reveals_the_word(client):
    data = client.post("/games/orquantix/give-up").get_json()

    assert data["word"] == "chien"
    assert data["gave_up"] is True
    assert data["temperature"] == 100.0


def test_state_survives_between_requests(client):
    client.post("/games/orquantix/guess", json={"word": "chat"})
    data = client.get("/games/orquantix/session").get_json()

    # C'est ce qui rend la navigation par pages viable.
    assert len(data["guesses"]) == 1
    assert data["guesses"][0]["word"] == "chat"


def test_new_game_resets_the_guesses(client):
    client.post("/games/orquantix/guess", json={"word": "chat"})
    client.post("/games/orquantix/new-game")
    data = client.get("/games/orquantix/session").get_json()

    assert data["guesses"] == []


def test_routes_refuse_when_not_ready(state):
    state.phase = "loading"
    app = Flask(__name__)
    app.register_blueprint(build_blueprint(state))
    app.config["TESTING"] = True

    with app.test_client() as c:
        assert c.post("/games/orquantix/guess", json={"word": "chat"}).status_code == 503


# Le reste ci-dessous restitue de la couverture perdue avec la suppression de
# tests/test_app.py : /suggest, /hint et /status n'étaient pas dans la liste
# donnée par le brief mais existaient dans l'ancienne suite.


def test_guess_missing_word_is_rejected(client):
    assert client.post("/games/orquantix/guess", json={}).status_code == 400


def test_status_reports_the_phase(client):
    data = client.get("/games/orquantix/status").get_json()
    assert data["phase"] == "ready"


def test_suggest_finds_close_word(client):
    data = client.post("/games/orquantix/suggest", json={"word": "chein"}).get_json()
    assert data["suggestion"] == "chien"


def test_suggest_missing_word_is_rejected(client):
    assert client.post("/games/orquantix/suggest", json={}).status_code == 400


def test_hint_first_letter(client):
    data = client.post("/games/orquantix/hint", json={"type": "first-letter"}).get_json()
    assert data["value"] == "c"


def test_hint_word_length(client):
    data = client.post("/games/orquantix/hint", json={"type": "word-length"}).get_json()
    assert data["value"] == 5


def test_hint_better_word_offers_a_pool_word_by_default(client, state):
    data = client.post("/games/orquantix/hint", json={"type": "better-word"}).get_json()
    assert data["value"] in state.pools.hint_words


def test_hint_better_word_never_crosses_the_hint_pool(client, state):
    # Régression pour l'obligation 1 : app.py passait frozenset(top1000), pas
    # le vrai pool d'indices. Un pool vide doit donc rendre value=None — s'il
    # retombait sur top1000 au lieu du pool, ce test échouerait.
    state.pools = Pools(
        mystery_words=state.pools.mystery_words,
        mystery_freq=state.pools.mystery_freq,
        hint_words=frozenset(),
    )
    data = client.post("/games/orquantix/hint", json={"type": "better-word"}).get_json()
    assert data["value"] is None


def test_hint_golden_fish_never_crosses_the_hint_pool(client, state):
    # Même régression que ci-dessus, pour le poisson doré (obligations 1 et 4).
    # littre est None dans la fixture, donc golden_fish retombe sur
    # strong_hint_word, qui doit lui aussi respecter le pool vide.
    state.pools = Pools(
        mystery_words=state.pools.mystery_words,
        mystery_freq=state.pools.mystery_freq,
        hint_words=frozenset(),
    )
    data = client.post("/games/orquantix/hint", json={"type": "golden-fish"}).get_json()
    assert data["value"] is None
    assert data["kind"] == "none"


def test_new_game_increments_the_game_index(client, state):
    assert state.game_index == 0
    client.post("/games/orquantix/new-game")
    assert state.game_index == 1


def test_new_game_response_has_difficulty_and_word_length(client):
    data = client.post("/games/orquantix/new-game").get_json()
    assert 1 <= data["difficulty"] <= 5
    assert data["word_length"] > 0
