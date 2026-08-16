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
