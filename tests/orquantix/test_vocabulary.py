import pytest

from games.orquantix.vocabulary import (
    build_norm_map,
    build_pools,
    compute_difficulty_thresholds,
    normalize,
)

LEXIQUE_TSV = (
    "ortho\tlemme\tcgram\tgenre\tnombre\tfreqlemlivres\n"
    # nom singulier dans la bande -> mystère ET indice
    "table\ttable\tNOM\tf\ts\t150.0\n"
    # nom trop fréquent -> indice seulement
    "homme\thomme\tNOM\tm\ts\t900.0\n"
    # nom trop rare -> indice seulement
    "parvis\tparvis\tNOM\tm\ts\t6.0\n"
    # nom sous le plancher des indices -> exclu partout
    "souchet\tsouchet\tNOM\tm\ts\t2.0\n"
    # pluriel -> exclu partout
    "tables\ttable\tNOM\tf\tp\t150.0\n"
    # verbe infinitif -> indice seulement
    "confire\tconfire\tVER\t\t\t20.0\n"
    # verbe conjugué -> exclu
    "confit\tconfire\tVER\t\t\t20.0\n"
    # adjectif masculin singulier -> indice seulement
    "glacial\tglacial\tADJ\tm\ts\t30.0\n"
    # adjectif féminin -> exclu
    "glaciale\tglacial\tADJ\tf\ts\t30.0\n"
    # apostrophe -> exclu
    "aujourd'hui\taujourd'hui\tNOM\tm\ts\t200.0\n"
    # absent du modèle -> exclu
    "fantome\tfantome\tNOM\tm\ts\t150.0\n"
)

MODEL_VOCAB = {
    "table", "homme", "parvis", "souchet", "tables",
    "confire", "confit", "glacial", "glaciale", "aujourd'hui",
}


@pytest.fixture
def lexique(tmp_path):
    path = tmp_path / "Lexique383.tsv"
    path.write_text(LEXIQUE_TSV, encoding="utf-8")
    return str(path)


def test_mystery_pool_keeps_only_nouns_in_the_frequency_band(lexique):
    pools = build_pools(lexique, MODEL_VOCAB)

    assert pools.mystery_words == ["table"]


def test_mystery_pool_excludes_too_frequent_and_too_rare(lexique):
    pools = build_pools(lexique, MODEL_VOCAB)

    assert "homme" not in pools.mystery_words   # 900 >= 400
    assert "parvis" not in pools.mystery_words  # 6 < 10


def test_hint_pool_keeps_content_words(lexique):
    pools = build_pools(lexique, MODEL_VOCAB)

    assert "table" in pools.hint_words
    assert "confire" in pools.hint_words   # verbe infinitif : bon indice
    assert "glacial" in pools.hint_words   # adjectif masc. sing.
    assert "homme" in pools.hint_words     # fréquent mais légitime en indice
    assert "parvis" in pools.hint_words    # rare mais au-dessus du plancher


def test_hint_pool_excludes_inflected_forms_and_junk(lexique):
    pools = build_pools(lexique, MODEL_VOCAB)

    assert "tables" not in pools.hint_words       # pluriel
    assert "confit" not in pools.hint_words       # conjugué
    assert "glaciale" not in pools.hint_words     # féminin
    assert "aujourd'hui" not in pools.hint_words  # apostrophe
    assert "souchet" not in pools.hint_words      # sous le plancher


def test_pool_excludes_words_absent_from_the_model(lexique):
    pools = build_pools(lexique, MODEL_VOCAB)

    assert "fantome" not in pools.hint_words
    assert "fantome" not in pools.mystery_words


def test_mystery_pool_is_sorted_by_descending_frequency(tmp_path):
    tsv = (
        "ortho\tlemme\tcgram\tgenre\tnombre\tfreqlemlivres\n"
        "table\ttable\tNOM\tf\ts\t150.0\n"
        "corde\tcorde\tNOM\tf\ts\t50.0\n"
        "lucarne\tlucarne\tNOM\tf\ts\t12.0\n"
    )
    path = tmp_path / "l.tsv"
    path.write_text(tsv, encoding="utf-8")

    pools = build_pools(str(path), {"table", "corde", "lucarne"})

    assert pools.mystery_words == ["table", "corde", "lucarne"]
    assert pools.mystery_freq["lucarne"] == 12.0


def test_normalize_and_norm_map_unchanged():
    assert normalize("Église") == "eglise"
    assert build_norm_map(["Église"]) == {"eglise": "Église"}


def test_compute_difficulty_thresholds_ascending():
    vocab = [f"w{i}" for i in range(100)]
    freq = {w: float(i) for i, w in enumerate(vocab)}

    thresholds = compute_difficulty_thresholds(vocab, freq)

    assert len(thresholds) == 4
    assert thresholds == sorted(thresholds)


# Fixture avec les seuils exacts pour tester les limites
LEXIQUE_BOUNDARIES = (
    "ortho\tlemme\tcgram\tgenre\tnombre\tfreqlemlivres\n"
    # Limite inférieure mystère : 10.0 exact (inclus)
    "mot_10_00\tmot_10_00\tNOM\tm\ts\t10.0\n"
    # Juste en dessous de la limite inférieure mystère : 9.99 (exclu)
    "mot_9_99\tmot_9_99\tNOM\tm\ts\t9.99\n"
    # Limite supérieure mystère : 400.0 exact (exclu)
    "mot_400_00\tmot_400_00\tNOM\tm\ts\t400.0\n"
    # Juste en dessous de la limite supérieure mystère : 399.99 (inclus)
    "mot_399_99\tmot_399_99\tNOM\tm\ts\t399.99\n"
    # Limite inférieure indice : 5.0 exact (inclus)
    "mot_5_00\tmot_5_00\tNOM\tm\ts\t5.0\n"
    # Juste en dessous de la limite inférieure indice : 4.99 (exclu)
    "mot_4_99\tmot_4_99\tNOM\tm\ts\t4.99\n"
)


@pytest.fixture
def lexique_boundaries(tmp_path):
    path = tmp_path / "boundaries.tsv"
    path.write_text(LEXIQUE_BOUNDARIES, encoding="utf-8")
    return str(path)


def test_mystery_pool_lower_boundary_inclusive(lexique_boundaries):
    """freqlemlivres == 10.0 doit être inclus dans le pool mystère."""
    model_vocab = {"mot_10_00"}
    pools = build_pools(lexique_boundaries, model_vocab)

    assert "mot_10_00" in pools.mystery_words


def test_mystery_pool_below_lower_boundary(lexique_boundaries):
    """freqlemlivres == 9.99 doit être exclu du pool mystère."""
    model_vocab = {"mot_9_99"}
    pools = build_pools(lexique_boundaries, model_vocab)

    assert "mot_9_99" not in pools.mystery_words


def test_mystery_pool_upper_boundary_exclusive(lexique_boundaries):
    """freqlemlivres == 400.0 doit être exclu du pool mystère (limite supérieure exclusive)."""
    model_vocab = {"mot_400_00"}
    pools = build_pools(lexique_boundaries, model_vocab)

    assert "mot_400_00" not in pools.mystery_words


def test_mystery_pool_below_upper_boundary(lexique_boundaries):
    """freqlemlivres == 399.99 doit être inclus dans le pool mystère."""
    model_vocab = {"mot_399_99"}
    pools = build_pools(lexique_boundaries, model_vocab)

    assert "mot_399_99" in pools.mystery_words


def test_hint_pool_lower_boundary_inclusive(lexique_boundaries):
    """freqlemlivres == 5.0 doit être inclus dans le pool d'indice."""
    model_vocab = {"mot_5_00"}
    pools = build_pools(lexique_boundaries, model_vocab)

    assert "mot_5_00" in pools.hint_words


def test_hint_pool_below_lower_boundary(lexique_boundaries):
    """freqlemlivres == 4.99 doit être exclu du pool d'indice."""
    model_vocab = {"mot_4_99"}
    pools = build_pools(lexique_boundaries, model_vocab)

    assert "mot_4_99" not in pools.hint_words


def test_boundary_interaction_400_in_hint_not_mystery(lexique_boundaries):
    """Un mot à 400.0 : exclu du mystère mais inclus dans les indices."""
    model_vocab = {"mot_400_00"}
    pools = build_pools(lexique_boundaries, model_vocab)

    assert "mot_400_00" not in pools.mystery_words  # exclu du mystère
    assert "mot_400_00" in pools.hint_words         # inclus dans les indices


def test_normalize_strips_diacritics():
    """normalize() doit enlever les accents et les accents courants."""
    assert normalize("naïf") == "naif"


def test_normalize_expands_ligatures():
    """normalize() doit développer les ligatures (transformation unidecode)."""
    assert normalize("cœur") == "coeur"
