from games.orquantix.hints import better_hint_word, golden_fish, strong_hint_word

# Voisinage réaliste : le modèle brut mélange mots de contenu, mots-outils
# et noms propres. Seuls les premiers appartiennent au pool d'indices.
TOP1000 = {
    "confire": 1,
    "des": 2,          # déterminant — jamais un indice valable
    "compote": 3,
    "jupiter": 4,      # nom propre — absent de Lexique383
    "souvent": 5,      # adverbe
    "coing": 6,
    "sorbet": 7,
    "leurs": 8,
    "sirop": 9,
    "amande": 10,
    "marron": 400,
    "orge": 850,
    "chardon": 900,
}

HINT_WORDS = frozenset(
    {"confire", "compote", "coing", "sorbet", "sirop", "amande", "marron", "orge", "chardon"}
)


def test_hints_never_return_a_word_outside_the_hint_pool():
    # Le test qui aurait attrapé « essaie des » et « essaie jupiter ».
    for best_rank in [None, 1000, 500, 100, 20, 5]:
        word = better_hint_word(TOP1000, HINT_WORDS, best_rank, set())
        assert word is None or word in HINT_WORDS, f"{word} n'est pas un indice valable"


def test_strong_hint_never_returns_a_function_word():
    word = strong_hint_word(TOP1000, HINT_WORDS, set())

    assert word in HINT_WORDS
    assert word not in {"des", "souvent", "leurs", "jupiter"}


def test_strong_hint_prefers_the_closest_eligible_neighbour():
    # « confire » est rang 1 et éligible.
    assert strong_hint_word(TOP1000, HINT_WORDS, set()) == "confire"


def test_strong_hint_skips_already_guessed_words():
    word = strong_hint_word(TOP1000, HINT_WORDS, {"confire", "compote"})

    assert word not in {"confire", "compote"}
    assert word in HINT_WORDS


def test_better_hint_improves_on_the_current_best_rank():
    word = better_hint_word(TOP1000, HINT_WORDS, best_rank=900, guessed=set())

    assert word is not None
    assert TOP1000[word] < 900


def test_better_hint_returns_none_when_already_at_rank_one():
    assert better_hint_word(TOP1000, HINT_WORDS, best_rank=1, guessed=set()) is None


def test_better_hint_with_no_guesses_yet_starts_far_out():
    word = better_hint_word(TOP1000, HINT_WORDS, best_rank=None, guessed=set())

    assert word in HINT_WORDS


class _FakeLittre:
    def __init__(self, entries):
        self._entries = entries

    def lookup(self, word, max_chars=220):
        return self._entries.get(word)


def test_golden_fish_returns_the_definition_when_available():
    littre = _FakeLittre({"confiture": "Fruits cuits avec du sucre."})

    result = golden_fish("confiture", littre, TOP1000, HINT_WORDS, set())

    assert result["kind"] == "definition"
    assert "Fruits cuits" in result["value"]


def test_golden_fish_falls_back_to_a_strong_neighbour_when_absent():
    # Les 74 mots modernes du pool : avion, cinéma, autoroute…
    littre = _FakeLittre({})

    result = golden_fish("avion", littre, TOP1000, HINT_WORDS, set())

    assert result["kind"] == "word"
    assert result["value"] in HINT_WORDS


def test_golden_fish_fallback_never_leaks_a_function_word():
    littre = _FakeLittre({})

    result = golden_fish("avion", littre, TOP1000, HINT_WORDS, set())

    assert result["value"] not in {"des", "souvent", "leurs", "jupiter"}
