import struct
from pathlib import Path

import pytest

from games.orquantix.dictionary import (
    Littre,
    clean_definition,
    fold,
    load_index,
)

REAL_DIR = Path.home() / "Library" / "Application Support" / "Orquantix"
REAL_AVAILABLE = (REAL_DIR / "XMLittre.idx").exists()


def test_fold_uppercases_and_strips_accents():
    assert fold("nausée") == "NAUSEE"
    assert fold("Confiture") == "CONFITURE"
    assert fold("étrier") == "ETRIER"


def test_load_index_parses_null_terminated_entries(tmp_path):
    # Format : MOT\0 + offset (>I) + longueur (>I)
    blob = b""
    blob += b"CONFITURE\x00" + struct.pack(">II", 100, 42)
    blob += b"GENOU\x00" + struct.pack(">II", 200, 17)
    idx = tmp_path / "test.idx"
    idx.write_bytes(blob)

    index = load_index(idx)

    assert index["CONFITURE"] == (100, 42)
    assert index["GENOU"] == (200, 17)
    assert len(index) == 2


def test_load_index_keeps_first_entry_on_collision(tmp_path):
    # "-ACE" et "-ACÉ" se replient tous deux sur "-ACE"
    blob = b""
    blob += "-ACE\x00".encode("utf-8") + struct.pack(">II", 10, 5)
    blob += "-ACÉ\x00".encode("utf-8") + struct.pack(">II", 99, 9)
    idx = tmp_path / "collide.idx"
    idx.write_bytes(blob)

    index = load_index(idx)

    assert index["-ACE"] == (10, 5)


CONFITURE_RAW = (
    "<i><small>(kon-fi-tu-r') s. f. On l'emploie souvent au pluriel. "
    "Fruits entiers ou coupés par morceaux, qu'on met cuire avec du sucre "
    "ou du sirop, et qui se transforment en une sorte de marmelade. "
    "Confitures de groseilles, de prunes. "
    "Un jeune Grec m'offrit des confitures, CHATEAUBR., Itinéraire.</small></i>"
)

GENOU_RAW = (
    "(je-nou. Chifflet dit que ce mot, s'écrivant genouil, se prononçait "
    "néanmoins genou) s. m. 1° Partie antérieure de l'articulation de la "
    "cuisse avec la jambe. 2° Il se dit aussi chez les quadrupèdes."
)


def test_clean_definition_strips_phonetic_prefix():
    # Le piège central : "(kon-fi-tu-r')" epelle le mot.
    cleaned = clean_definition(CONFITURE_RAW, "confiture")

    assert "kon-fi-tu-r" not in cleaned
    assert not cleaned.startswith("(")


def test_clean_definition_strips_long_phonetic_parenthesis():
    # Pour "genou" la parenthese est longue et contient le mot deux fois.
    cleaned = clean_definition(GENOU_RAW, "genou")

    assert "je-nou" not in cleaned
    assert "genouil" not in cleaned
    assert "Partie antérieure" in cleaned


def test_clean_definition_masks_the_target_word_family():
    cleaned = clean_definition(CONFITURE_RAW, "confiture")

    assert "confiture" not in cleaned.lower()
    assert "confitures" not in cleaned.lower()


def test_clean_definition_removes_markup():
    cleaned = clean_definition(CONFITURE_RAW, "confiture")

    assert "<" not in cleaned
    assert ">" not in cleaned


def test_clean_definition_keeps_the_useful_content():
    cleaned = clean_definition(CONFITURE_RAW, "confiture")

    assert "Fruits entiers" in cleaned


def test_clean_definition_stops_at_the_second_sense():
    cleaned = clean_definition(GENOU_RAW, "genou")

    assert "quadrupèdes" not in cleaned


def test_clean_definition_truncates_to_max_chars():
    cleaned = clean_definition(CONFITURE_RAW, "confiture", max_chars=60)

    assert len(cleaned) <= 61  # 60 + l'ellipse
    assert cleaned.endswith("…")


def test_clean_definition_returns_empty_when_nothing_survives():
    assert clean_definition("(a-b-c) s. f.", "abc") == ""


# Les deux tests suivants ne sont pas dans le brief : ils couvrent deux fuites
# trouvées en validant contre le vrai Littré (mot "avant-hier" et "chien"),
# absentes des fixtures synthétiques du brief.


def test_clean_definition_masks_hyphenated_compound_target():
    # "avant-hier" apparaît littéralement dans sa propre définition Littré ;
    # le tokenizer de masquage doit traiter le composé comme un seul mot,
    # pas comme "avant" et "hier" séparés par la frontière du tiret.
    raw = "de temps. Le bruit court qu'avant-hier on vous assassina, BOILEAU."
    cleaned = clean_definition(raw, "avant-hier")

    assert "avant-hier" not in cleaned.lower()


def test_clean_definition_strips_chained_leading_parentheses():
    # Entrées à double genre (ex. "chien") : une parenthèse phonétique,
    # un marqueur grammatical, puis une deuxième parenthèse ("(le mâle)")
    # avant le second marqueur grammatical. Il faut boucler, pas s'arrêter
    # après le premier groupe parenthèse+marqueur.
    raw = "(chiin, chièn') s. m. (le mâle), s. f. (la femelle) Quadrupède domestique."
    cleaned = clean_definition(raw, "chien")

    assert not cleaned.startswith("(")
    assert "chiin" not in cleaned
    assert "Quadrupède domestique" in cleaned


def test_littre_lookup_returns_none_for_absent_word(tmp_path):
    idx = tmp_path / "x.idx"
    idx.write_bytes(b"CONFITURE\x00" + struct.pack(">II", 0, 10))
    import gzip

    dict_path = tmp_path / "x.dict.dz"
    with gzip.open(dict_path, "wb") as f:
        f.write(b"peu importe")

    littre = Littre(idx, dict_path)

    assert littre.lookup("avion") is None
    assert "avion" not in littre
    assert "confiture" in littre


def test_littre_lookup_cleans_the_entry(tmp_path):
    import gzip

    body = "(kon-fi-tu-r') s. f. Fruits cuits avec du sucre.".encode("utf-8")
    dict_path = tmp_path / "y.dict.dz"
    with gzip.open(dict_path, "wb") as f:
        f.write(body)

    idx = tmp_path / "y.idx"
    idx.write_bytes(b"CONFITURE\x00" + struct.pack(">II", 0, len(body)))

    littre = Littre(idx, dict_path)
    definition = littre.lookup("confiture")

    assert "kon-fi-tu-r" not in definition
    assert "Fruits cuits" in definition


@pytest.mark.skipif(not REAL_AVAILABLE, reason="Littré non téléchargé")
def test_real_littre_never_leaks_the_word():
    littre = Littre(REAL_DIR / "XMLittre.idx", REAL_DIR / "XMLittre.dict.dz")

    for word in ["confiture", "genou", "lucarne", "nausée", "gravure"]:
        definition = littre.lookup(word)
        assert definition is not None, word
        assert word not in definition.lower(), f"{word} fuite dans sa propre définition"
        assert not definition.startswith("("), word
