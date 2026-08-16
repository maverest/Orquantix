import gzip
import random
import struct
from pathlib import Path

import pytest

from games.orquantix.dictionary import (
    Littre,
    clean_definition,
    fold,
    load_index,
)
from games.orquantix.dictionary import (
    _GRAMMAR_MARKER,
    _LEADING_ALT_HEADWORD,
    _LEADING_CONNECTIVE,
    _LEADING_JUNCTION,
    _LEADING_PARENS,
    _LEADING_SENSE,
    _PHONETIC_PAREN,
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
    # avant le second marqueur grammatical, elle-même suivie d'une virgule
    # de jonction ("(le mâle), s. f. …") qui bloquait les regex ancrées
    # suivantes une fois le premier groupe consommé. Il faut boucler et
    # avaler cette virgule, pas s'arrêter après le premier groupe.
    raw = (
        "(chiin, chièn') s. m. (le mâle), s. f. (la femelle) "
        "1° Quadrupède domestique."
    )
    cleaned = clean_definition(raw, "chien")

    # Assertions sur le contenu réel, pas seulement l'absence de "(" en tête :
    # une version cassée peut très bien commencer par une virgule et passer
    # un test qui ne vérifie que "not startswith('(')".
    assert cleaned.startswith("Quadrupède domestique")
    assert not cleaned.startswith("(")
    assert "chiin" not in cleaned
    assert "s. f." not in cleaned
    assert "(la femelle)" not in cleaned
    assert "1°" not in cleaned


# Les cinq tests suivants couvrent la deuxième passe de correction (finding
# "Critical" : des transcriptions phonétiques de la famille du mot cible
# survivaient dans le rendu final sur de vraies entrées). Chacun isole une
# combinaison de structure de tête trouvée en vrai, pas seulement les mots
# du rapport de finding — le défaut général était que le nettoyeur de tête
# ne consommait qu'une chaîne figée (parenthèse, marqueur grammatical,
# jonction) et s'arrêtait dès qu'un autre type de jeton structurel
# apparaissait en tête.


def test_clean_definition_strips_leading_alternate_headword_with_own_phonetic():
    # "ogre" : la forme féminine alternative "OGRESSE" et sa propre
    # parenthèse phonétique se trouvent entre la première parenthèse et le
    # marqueur grammatical — le nettoyeur de tête doit les avaler aussi, pas
    # seulement la première parenthèse rencontrée.
    raw = "(o-gr'), OGRESSE (o-grè-s'), s. m. et f. 1° Espèce de monstre."
    cleaned = clean_definition(raw, "ogre")

    assert cleaned == "Espèce de monstre."
    assert "o-grè-s" not in cleaned
    assert "OGRESSE" not in cleaned


def test_clean_definition_strips_connective_before_alternate_headword():
    # "escarbit" : le connecteur "ou" précède la variante alternative et sa
    # parenthèse phonétique — sans ce connecteur reconnu comme structurel,
    # la boucle de nettoyage de tête atteint un faux point fixe trop tôt.
    raw = "(è-skar-bit'), s. m. ou ESCARBITE (è-skar-bi-t'), s. f. Terme de marine."
    cleaned = clean_definition(raw, "escarbit")

    assert cleaned == "Terme de marine."
    assert "è-skar-bi-t" not in cleaned
    assert "ESCARBITE" not in cleaned


def test_clean_definition_strips_leading_supplement_sense_marker():
    # Une entrée de supplément peut commencer directement par son propre
    # numéro de sens ("2." — point, pas le signe degré "°" du corps
    # principal) suivi du mot-vedette et de sa parenthèse phonétique.
    raw = "2. TROQUET (tro-kè), s. m. Nom vulgaire du maïs."
    cleaned = clean_definition(raw, "troquet")

    assert cleaned == "Nom vulgaire du maïs."
    assert "tro-kè" not in cleaned
    assert "TROQUET" not in cleaned


def test_clean_definition_strips_phonetic_parenthesis_anywhere_in_text():
    # Le filet de sécurité indépendant : une parenthèse de forme phonétique
    # qui ne se trouve PAS en tête (ex. après une bannière de supplément au
    # milieu du texte, cas réel de "troquet") doit quand même sauter. Le
    # nettoyeur de tête, par construction, ne regarde qu'en position 0 et ne
    # peut pas voir celle-ci.
    raw = (
        "Terme de couvreur. Chevalet du comble SUPPLÉMENT AU DICTIONNAIRE "
        "2. TROQUET (tro-kè), s. m. Nom vulgaire du maïs."
    )
    cleaned = clean_definition(raw, "troquet")

    assert "tro-kè" not in cleaned
    assert "Terme de couvreur" in cleaned


def test_clean_definition_masks_irregular_man_men_plural():
    # "yeoman"/"yeomen" : le pluriel anglais irrégulier fait diverger le mot
    # exactement dans la fenêtre du préfixe utilisée par le masquage normal
    # ("yeoma" vs "yeome"), qui échappe donc au test startswith habituel.
    raw = "au pluriel YEOMEN (iomèn), s. m. Membre de la yeomanry. Les yeomen."
    cleaned = clean_definition(raw, "yeoman")

    assert "yeomen" not in cleaned.lower()
    assert "iomèn" not in cleaned


def test_littre_lookup_returns_none_for_absent_word(tmp_path):
    idx = tmp_path / "x.idx"
    idx.write_bytes(b"CONFITURE\x00" + struct.pack(">II", 0, 10))

    dict_path = tmp_path / "x.dict.dz"
    with gzip.open(dict_path, "wb") as f:
        f.write(b"peu importe")

    littre = Littre(idx, dict_path)

    assert littre.lookup("avion") is None
    assert "avion" not in littre
    assert "confiture" in littre


def test_littre_lookup_cleans_the_entry(tmp_path):
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


# Le test suivant est le vrai livrable de la deuxième passe de correction :
# la vérification, dans les deux passes précédentes, ne portait que sur une
# poignée de mots choisis à la main, ce qui a laissé passer le défaut deux
# fois de suite. Ce test balaie un échantillon déterministe et substantiel
# de vraies entrées Littré (échantillonnage aléatoire à graine fixe sur les
# ~93 000 entrées de l'index réel, sans jamais toutes les traiter) et
# affirme l'invariant central du module directement, plutôt que sur des
# exemples choisis à l'avance :
#   - aucune parenthèse de forme phonétique ne doit subsister nulle part
#     dans le texte nettoyé (filet indépendant, cf. _PHONETIC_PAREN) ;
#   - aucun marqueur structurel de tête (parenthèse, marqueur grammatical,
#     jonction, connecteur, mot-vedette alternatif, marqueur de sens) ne
#     doit subsister en tête du texte nettoyé ;
#   - aucun jeton du texte nettoyé ne doit être, une fois replié, strictement
#     égal au mot cible replié (aucune fuite littérale du mot-vedette).
_REAL_SWEEP_SEED = 20260816
_REAL_SWEEP_SAMPLE_SIZE = 8000

_LEADING_STRUCTURE_PATTERNS = (
    _LEADING_PARENS,
    _GRAMMAR_MARKER,
    _LEADING_JUNCTION,
    _LEADING_CONNECTIVE,
    _LEADING_ALT_HEADWORD,
    _LEADING_SENSE,
)


@pytest.mark.skipif(not REAL_AVAILABLE, reason="Littré non téléchargé")
def test_real_littre_sweep_has_no_residual_leak():
    littre = Littre(REAL_DIR / "XMLittre.idx", REAL_DIR / "XMLittre.dict.dz")
    index = load_index(REAL_DIR / "XMLittre.idx")

    keys = sorted(index)
    sample = random.Random(_REAL_SWEEP_SEED).sample(
        keys, min(_REAL_SWEEP_SAMPLE_SIZE, len(keys))
    )

    phonetic_leaks = []
    leading_leaks = []
    headword_leaks = []

    for key in sample:
        cleaned = littre.lookup(key)
        if cleaned is None:
            continue

        if _PHONETIC_PAREN.search(cleaned):
            phonetic_leaks.append((key, cleaned))

        if any(pattern.match(cleaned) for pattern in _LEADING_STRUCTURE_PATTERNS):
            leading_leaks.append((key, cleaned))

        # Vérification bonus, au-delà de ce que ce correctif demande : aucun
        # jeton du texte nettoyé ne doit être, replié, strictement égal au
        # mot-vedette replié. Exclut les ~0,8 % de clés d'index contenant une
        # apostrophe ("S'ABSTENIR", "D'EMBLEE" ...) : le tokenizer de
        # _mask_family traite l'apostrophe comme une frontière dure (ce qui
        # est nécessaire ailleurs, ex. "qu'avant-hier" doit isoler "avant-
        # hier" comme un jeton propre), ce qui fait qu'un mot-vedette
        # contenant lui-même une apostrophe n'est jamais reconnu par le
        # préfixe replié qui, lui, la conserve. C'est un défaut préexistant,
        # distinct de la structure de tête (root cause de ce correctif), qui
        # touche des entrées de type locution/verbe pronominal improbables
        # comme mot mystère du jeu — documenté, non corrigé ici.
        if "'" not in key:
            folded_target = fold(key)
            folded_tokens = fold(cleaned).replace("-", " ").split()
            if folded_target in folded_tokens:
                headword_leaks.append((key, cleaned))

    assert not phonetic_leaks, (
        f"{len(phonetic_leaks)}/{len(sample)} parenthèse(s) phonétique(s) "
        f"résiduelle(s), ex. : {phonetic_leaks[:5]}"
    )
    assert not leading_leaks, (
        f"{len(leading_leaks)}/{len(sample)} structure(s) de tête "
        f"résiduelle(s), ex. : {leading_leaks[:5]}"
    )
    assert not headword_leaks, (
        f"{len(headword_leaks)}/{len(sample)} fuite(s) littérale(s) du "
        f"mot-vedette, ex. : {headword_leaks[:5]}"
    )
