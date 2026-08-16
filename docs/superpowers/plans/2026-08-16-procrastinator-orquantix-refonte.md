# PROCRASTINATOR — Refonte d'Orquantix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformer l'application en PROCRASTINATOR, une coquille hébergeant des mini-jeux, et refondre Orquantix — le premier d'entre eux — autour d'une température continue, de pools de vocabulaire resserrés, d'indices débogués et d'un poisson doré qui lit le dictionnaire Littré.

**Architecture:** Orquantix devient un paquet Python autonome (`games/orquantix/`) exposant un blueprint Flask monté sous `/games/orquantix/`. `app.py` devient une coquille qui n'a aucune connaissance des règles d'Orquantix. L'état de partie vit côté serveur dans `OrquantixState`, ce qui rend la navigation par pages viable. Les ressources lourdes sont chargées à l'entrée dans le jeu, pas au démarrage.

**Tech Stack:** Python 3.12, Flask, gensim (KeyedVectors), pywebview, rapidfuzz, pytest, PyInstaller.

## Global Constraints

- **Spec de référence :** `docs/superpowers/specs/2026-08-16-procrastinator-orquantix-refonte-design.md`
- **Branche de travail :** `spec/procrastinator-refonte` (déjà créée, contient le commit de spec)
- **Nom de l'application :** PROCRASTINATOR. **Nom du mini-jeu :** Orquantix. Ne jamais confondre les deux.
- **Pool des mots mystères :** noms communs Lexique383, `nombre ∈ {s, ""}`, sans espace/tiret/apostrophe, `freqlemlivres` dans `[10.0, 400.0)`, présents dans le modèle. Taille attendue : **2 788**.
- **Pool des indices :** mêmes contraintes de forme, `cgram ∈ {NOM sing., VER infinitif, ADJ masc. sing.}`, `freqlemlivres >= 5.0`. Taille attendue : **6 916**.
- **Vocabulaire de proposition :** inchangé, les 31 548 mots du modèle.
- **Température :** trois ancres — `floor` = médiane des cosinus, `top1000` = cosinus du 1000ᵉ voisin, `maximum` = cosinus du 1ᵉʳ voisin. 50° = entrée dans le top 1000. Rang 1 plafonne à 99°. 100° réservé à la victoire.
- **Seuils d'humeur (température) :** `< 20` sick, `< 50` vexed, `< 70` intrigued, `< 88` overexcited, `< 100` solar, `== 100` found.
- **Dictionnaire :** Littré, `XMLittre.idx` + `XMLittre.dict.dz`. Index : suite de `MOT\0` + offset `>I` + longueur `>I`.
- **Langue de l'interface et des messages joueur :** français.
- **Aucun `<script>` inline** dans les templates à la fin du chantier.
- **Tests verts à chaque commit.** Aucun commit ne doit laisser la suite rouge.

---

## File Structure

**Créés :**

| Fichier | Responsabilité |
|---|---|
| `.gitignore` | Exclure les sorties de build |
| `games/__init__.py` | Paquet des mini-jeux |
| `games/orquantix/__init__.py` | Expose le blueprint et le chargeur de ressources |
| `games/orquantix/dictionary.py` | Lecture et nettoyage des entrées Littré |
| `games/orquantix/vocabulary.py` | Construction des deux pools (déplacé puis réécrit) |
| `games/orquantix/engine.py` | Température, rang, tirage du mot, difficulté |
| `games/orquantix/orca.py` | Humeurs, libellés, emojis |
| `games/orquantix/hints.py` | Sélection d'indices et poisson doré |
| `games/orquantix/state.py` | `OrquantixState` |
| `games/orquantix/routes.py` | Blueprint Flask |
| `templates/orquantix/index.html` | Structure du jeu, sans script |
| `static/shell.css` | Tokens partagés |
| `static/orquantix/style.css` | Habillage du jeu |
| `static/orquantix/game.js` | Partie, tableau, température |
| `static/orquantix/orca.js` | Orque, modes, glisser-déposer |
| `tests/orquantix/*` | Tests du paquet |

**Modifiés :** `app.py` (devient la coquille), `main.py` (migration du dossier de données), `downloader.py` (trois fichiers), `README.md`, `requirements.txt`.

**Supprimés :** `game.py`, `vocabulary.py` (racine), `templates/index.html`, `static/style.css`, `Semantix.spec`, `Orquantix.spec`.

---

### Task 1: Environnement de développement et hygiène du dépôt

Aucun test ne tourne aujourd'hui : il n'existe pas de venv et `flask` n'est pas installé. Tout le reste du plan en dépend.

**Files:**
- Create: `.gitignore`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: rien
- Produces: un venv `.venv/` fonctionnel, la suite de 46 tests verte

- [ ] **Step 1: Créer le venv et installer les dépendances**

```bash
cd /Users/mverest/Desktop/Orquantix
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt
```

- [ ] **Step 2: Vérifier que gensim s'importe**

Run: `python -c "import flask, gensim, rapidfuzz, unidecode; print('ok')"`
Expected: `ok`

Si gensim échoue sur une incompatibilité numpy, forcer `pip install "gensim>=4.4"` puis relancer.

- [ ] **Step 3: Lancer la suite existante**

Run: `python -m pytest -q`
Expected: `50 passed`

C'est la ligne de base.

**Deux tests étaient périmés dans le dépôt d'origine** et ont été corrigés au démarrage du chantier : `test_get_progress_percent_inside_top1000` attendait `9.52` là où la formule donne `9.54`, et `test_get_proximity_feedback_for_ranked_guess` attendait `64.85` pour `65.0`. Le code était juste, les attentes fausses. Les deux tests visent des fonctions supprimées en Task 5.

- [ ] **Step 4: Écrire `.gitignore`**

```
__pycache__/
*.py[cod]

.venv/
.venv_build/

build/
dist/

.superpowers/
.DS_Store
```

- [ ] **Step 5: Détracker les sorties de build**

Ces répertoires sont des sorties de build (4 782 fichiers, 424 Mo). Vérification faite : tous les assets nécessaires au jeu (`static/orca_assets`, `static/easter_assets`, `static/proximity_assets`, `templates/`) restent suivis.

```bash
git rm -r --cached dist build __pycache__ tests/__pycache__ --quiet
git add .gitignore
git commit -m "chore: ajouter .gitignore et detracker les sorties de build"
```

- [ ] **Step 6: Vérifier que le dépôt reste jouable**

Run: `git ls-files static/ templates/ | wc -l`
Expected: `23` (20 assets + style.css + index.html + rien d'autre)

Run: `python -m pytest -q`
Expected: `46 passed`

---

### Task 2: Déplacer Orquantix dans son paquet — déplacement mécanique pur

Aucun changement de comportement. On sépare le déplacement de fichiers des changements de logique, pour que les diffs suivants soient lisibles.

**Files:**
- Create: `games/__init__.py`, `games/orquantix/__init__.py`
- Move: `game.py` → `games/orquantix/engine.py`, `vocabulary.py` → `games/orquantix/vocabulary.py`
- Modify: `app.py:8-24`, `tests/test_game.py`, `tests/test_app.py`, `tests/test_vocabulary.py`

**Interfaces:**
- Consumes: rien
- Produces: `games.orquantix.engine` et `games.orquantix.vocabulary` importables, avec exactement les mêmes fonctions qu'avant

- [ ] **Step 1: Créer le paquet**

```bash
mkdir -p games/orquantix tests/orquantix
touch games/__init__.py games/orquantix/__init__.py tests/orquantix/__init__.py
```

`games/__init__.py` et `games/orquantix/__init__.py` restent vides à ce stade.

- [ ] **Step 2: Déplacer les deux modules**

```bash
git mv game.py games/orquantix/engine.py
git mv vocabulary.py games/orquantix/vocabulary.py
```

- [ ] **Step 3: Mettre à jour les imports dans `app.py`**

Remplacer les deux blocs d'import en tête de `app.py` :

```python
from games.orquantix.engine import (
    get_better_hint_word,
    get_daily_word,
    get_difficulty,
    get_proximity_feedback,
    get_score,
    get_strong_hint_word,
    get_top1000,
)
from games.orquantix.vocabulary import (
    build_norm_map,
    compute_difficulty_thresholds,
    filter_eligible_words,
    normalize,
)
```

- [ ] **Step 4: Mettre à jour les imports dans les tests**

Dans `tests/test_game.py`, `tests/test_app.py`, `tests/test_vocabulary.py`, remplacer partout :

- `from game import` → `from games.orquantix.engine import`
- `from vocabulary import` → `from games.orquantix.vocabulary import`

Attention : `tests/test_game.py` contient des imports **à l'intérieur des fonctions de test** (`from game import get_daily_word`). Les traiter aussi.

Run: `grep -rn "^from game import\|^from vocabulary import\|from game import\|from vocabulary import" tests/ app.py`
Expected: aucune sortie

- [ ] **Step 5: Vérifier que rien n'a bougé**

Run: `python -m pytest -q`
Expected: `46 passed`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: deplacer game.py et vocabulary.py dans games/orquantix/"
```

---

### Task 3: Le dictionnaire Littré

Module le plus risqué et le plus isolé : il ne dépend de rien. La transcription phonétique en tête d'entrée épelle le mot — ne pas la retirer transformerait l'indice en réponse.

**Files:**
- Create: `games/orquantix/dictionary.py`
- Test: `tests/orquantix/test_dictionary.py`

**Interfaces:**
- Consumes: rien
- Produces:
  - `fold(word: str) -> str`
  - `load_index(idx_path: str | Path) -> dict[str, tuple[int, int]]`
  - `clean_definition(raw: str, target: str, max_chars: int = 220) -> str`
  - `class Littre` avec `.lookup(word: str) -> str | None` (définition nettoyée) et `.__contains__(word: str) -> bool`
  - `IDX_FILENAME = "XMLittre.idx"`, `DICT_FILENAME = "XMLittre.dict.dz"`

- [ ] **Step 1: Écrire les tests du repliement et de l'index**

Créer `tests/orquantix/test_dictionary.py` :

```python
import struct

import pytest

from games.orquantix.dictionary import (
    Littre,
    clean_definition,
    fold,
    load_index,
)


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
```

- [ ] **Step 2: Lancer les tests pour les voir échouer**

Run: `python -m pytest tests/orquantix/test_dictionary.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'games.orquantix.dictionary'`

- [ ] **Step 3: Implémenter le repliement et l'index**

Créer `games/orquantix/dictionary.py` :

```python
from __future__ import annotations

import gzip
import re
import struct
import unicodedata
from pathlib import Path

IDX_FILENAME = "XMLittre.idx"
DICT_FILENAME = "XMLittre.dict.dz"


def fold(word: str) -> str:
    """Majuscules sans accents — la forme utilisée comme clé d'index."""
    upper = word.upper()
    decomposed = unicodedata.normalize("NFD", upper)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def load_index(idx_path: str | Path) -> dict[str, tuple[int, int]]:
    """Parse l'index dictd : suite de MOT\\0 + offset (>I) + longueur (>I)."""
    raw = Path(idx_path).read_bytes()
    index: dict[str, tuple[int, int]] = {}
    position = 0
    total = len(raw)

    while position < total:
        separator = raw.index(b"\x00", position)
        word = raw[position:separator].decode("utf-8", "replace")
        offset, length = struct.unpack(">II", raw[separator + 1 : separator + 9])
        index.setdefault(fold(word), (offset, length))
        position = separator + 9

    return index
```

- [ ] **Step 4: Vérifier que ces trois tests passent**

Run: `python -m pytest tests/orquantix/test_dictionary.py -q`
Expected: `3 passed`

- [ ] **Step 5: Écrire les tests de nettoyage**

C'est le cœur du risque. Ajouter à `tests/orquantix/test_dictionary.py` :

```python
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
```

- [ ] **Step 6: Lancer pour voir échouer**

Run: `python -m pytest tests/orquantix/test_dictionary.py -q`
Expected: FAIL — `ImportError: cannot import name 'clean_definition'`

- [ ] **Step 7: Implémenter le nettoyage**

Ajouter à `games/orquantix/dictionary.py` :

```python
_TAG = re.compile(r"<[^>]+>")
_LEADING_PARENS = re.compile(r"^\s*\([^)]*\)\s*")
_GRAMMAR_MARKER = re.compile(
    r"^\s*(s\.\s*[mf]\.(\s*et\s*f\.)?|adj\.|v\.\s*[an]\.|adv\.)\s*",
    re.IGNORECASE,
)
_SECOND_SENSE = re.compile(r"\s*2°")
_FIRST_SENSE_MARKER = re.compile(r"^\s*1°\s*")
_CITATION = re.compile(r",?\s*[A-ZÀ-Ý]{4,}\.[^.]*\.")
_WHITESPACE = re.compile(r"\s+")


def _mask_family(text: str, target: str) -> str:
    """Masque le mot cible et sa famille morphologique."""
    folded = fold(target)
    prefix_length = max(5, len(folded) - 3)
    prefix = folded[:prefix_length]

    def replace(match: re.Match[str]) -> str:
        return "***" if fold(match.group(0)).startswith(prefix) else match.group(0)

    return re.sub(r"\b\w+\b", replace, text)


def clean_definition(raw: str, target: str, max_chars: int = 220) -> str:
    """Transforme une entrée Littré brute en un indice lisible.

    Ordre imposé : le balisage part en premier pour que la parenthèse
    phonétique devienne détectable en tête de chaîne.
    """
    text = _TAG.sub("", raw)
    text = _WHITESPACE.sub(" ", text).strip()

    # La transcription phonétique épelle le mot : elle doit sauter.
    text = _LEADING_PARENS.sub("", text)
    text = _GRAMMAR_MARKER.sub("", text)

    text = _SECOND_SENSE.split(text)[0]
    text = _FIRST_SENSE_MARKER.sub("", text)
    text = _CITATION.sub("", text)
    text = _mask_family(text, target)
    text = _WHITESPACE.sub(" ", text).strip()

    if len(text) > max_chars:
        cut = text[:max_chars].rsplit(" ", 1)[0]
        text = cut + "…"

    return text.strip()
```

- [ ] **Step 8: Lancer les tests de nettoyage**

Run: `python -m pytest tests/orquantix/test_dictionary.py -q`
Expected: `11 passed`

Si `test_clean_definition_keeps_the_useful_content` échoue parce que « On l'emploie souvent au pluriel » subsiste : c'est acceptable, ce n'est pas un giveaway. Ajuster l'assertion, pas le code.

- [ ] **Step 9: Écrire les tests de la classe `Littre`**

```python
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
```

- [ ] **Step 10: Implémenter `Littre`**

```python
class Littre:
    """Accès paresseux au dictionnaire Littré."""

    def __init__(self, idx_path: str | Path, dict_path: str | Path) -> None:
        self._index = load_index(idx_path)
        with gzip.open(dict_path, "rb") as handle:
            self._blob = handle.read()

    def __contains__(self, word: str) -> bool:
        return fold(word) in self._index

    def lookup(self, word: str, max_chars: int = 220) -> str | None:
        """Définition nettoyée, ou None si le mot est absent."""
        entry = self._index.get(fold(word))
        if entry is None:
            return None

        offset, length = entry
        raw = self._blob[offset : offset + length].decode("utf-8", "replace")
        cleaned = clean_definition(raw, word, max_chars=max_chars)
        return cleaned or None
```

- [ ] **Step 11: Lancer toute la suite**

Run: `python -m pytest -q`
Expected: `59 passed`

- [ ] **Step 12: Vérification sur les vraies données**

Ce test ne tourne que si les fichiers réels sont présents. Ajouter :

```python
import os
from pathlib import Path

REAL_DIR = Path.home() / "Library" / "Application Support" / "Orquantix"
REAL_AVAILABLE = (REAL_DIR / "XMLittre.idx").exists()


@pytest.mark.skipif(not REAL_AVAILABLE, reason="Littré non téléchargé")
def test_real_littre_never_leaks_the_word():
    littre = Littre(REAL_DIR / "XMLittre.idx", REAL_DIR / "XMLittre.dict.dz")

    for word in ["confiture", "genou", "lucarne", "nausée", "gravure"]:
        definition = littre.lookup(word)
        assert definition is not None, word
        assert word not in definition.lower(), f"{word} fuite dans sa propre définition"
        assert not definition.startswith("("), word
```

Run: `python -m pytest tests/orquantix/test_dictionary.py -q`
Expected: `14 passed`

- [ ] **Step 13: Commit**

```bash
git add games/orquantix/dictionary.py tests/orquantix/test_dictionary.py
git commit -m "feat: lecture et nettoyage du dictionnaire Littre"
```

---

### Task 4: Les deux pools de vocabulaire

Le pool de mots mystères se resserre aux noms communs de la bande 10–400/M ; l'ancien pool devient le réservoir d'indices. Un seul passage sur le TSV de 25 Mo produit les deux.

**Files:**
- Modify: `games/orquantix/vocabulary.py`
- Test: `tests/orquantix/test_vocabulary.py` (nouveau), `tests/test_vocabulary.py` (migré puis supprimé)

**Interfaces:**
- Consumes: rien
- Produces:
  - `@dataclass(frozen=True) class Pools` avec `mystery_words: list[str]`, `mystery_freq: dict[str, float]`, `hint_words: frozenset[str]`
  - `build_pools(tsv_path, model_vocab: set[str], *, mystery_min=10.0, mystery_max=400.0, hint_min=5.0) -> Pools`
  - `normalize(word) -> str` et `build_norm_map(words) -> dict[str, str]` — inchangés
  - `compute_difficulty_thresholds(vocab, freq_by_word) -> list[float]` — inchangé

- [ ] **Step 1: Écrire les tests des pools**

Créer `tests/orquantix/test_vocabulary.py` :

```python
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
```

- [ ] **Step 2: Lancer pour voir échouer**

Run: `python -m pytest tests/orquantix/test_vocabulary.py -q`
Expected: FAIL — `ImportError: cannot import name 'build_pools'`

- [ ] **Step 3: Réécrire `games/orquantix/vocabulary.py`**

Remplacer intégralement le contenu du fichier :

```python
from __future__ import annotations

import csv
from dataclasses import dataclass

from unidecode import unidecode

FORBIDDEN_CHARS = (" ", "-", "'")


def normalize(word: str) -> str:
    """Minuscules sans accents."""
    return unidecode(word.lower())


def build_norm_map(words: list[str]) -> dict[str, str]:
    """Forme normalisée → forme d'origine. Le dernier écrit gagne."""
    return {normalize(w): w for w in words}


@dataclass(frozen=True)
class Pools:
    """Les deux ensembles dérivés de Lexique383.

    mystery_words : cibles possibles, triées par fréquence décroissante.
    hint_words    : mots proposables comme indices.
    """

    mystery_words: list[str]
    mystery_freq: dict[str, float]
    hint_words: frozenset[str]


def _has_clean_form(ortho: str) -> bool:
    return not any(c in ortho for c in FORBIDDEN_CHARS)


def _is_singular_noun(cgram: str, nombre: str) -> bool:
    return cgram == "NOM" and nombre in ("s", "")


def _is_content_word(cgram: str, genre: str, nombre: str, ortho: str, lemme: str) -> bool:
    if _is_singular_noun(cgram, nombre):
        return True
    if cgram == "ADJ" and genre in ("m", "") and nombre in ("s", ""):
        return True
    if cgram == "VER" and ortho == lemme:  # infinitif : la forme égale le lemme
        return True
    return False


def build_pools(
    tsv_path: str,
    model_vocab: set[str],
    *,
    mystery_min: float = 10.0,
    mystery_max: float = 400.0,
    hint_min: float = 5.0,
) -> Pools:
    """Construit les deux pools en un seul passage sur Lexique383.

    Le pool d'indices est plus large que celui des mots mystères : un indice
    n'a pas à être un mot avec lequel on pourrait gagner, il doit orienter.
    """
    mystery_freq: dict[str, float] = {}
    hint_words: set[str] = set()

    with open(tsv_path, encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            ortho = row.get("ortho", "")
            if not ortho or ortho not in model_vocab or not _has_clean_form(ortho):
                continue

            cgram = row.get("cgram", "")
            genre = row.get("genre", "")
            nombre = row.get("nombre", "")
            lemme = row.get("lemme", "")

            try:
                freq = float(row.get("freqlemlivres") or 0)
            except ValueError:
                freq = 0.0

            if freq >= hint_min and _is_content_word(cgram, genre, nombre, ortho, lemme):
                hint_words.add(ortho)

            if _is_singular_noun(cgram, nombre) and mystery_min <= freq < mystery_max:
                if ortho not in mystery_freq or freq > mystery_freq[ortho]:
                    mystery_freq[ortho] = freq

    mystery_words = sorted(mystery_freq, key=mystery_freq.__getitem__, reverse=True)
    return Pools(
        mystery_words=mystery_words,
        mystery_freq=mystery_freq,
        hint_words=frozenset(hint_words),
    )


def compute_difficulty_thresholds(
    vocab: list[str],
    freq_by_word: dict[str, float],
) -> list[float]:
    """Quatre seuils croissants découpant le vocabulaire en quintiles."""
    freqs = sorted(freq_by_word.get(w, 0.0) for w in vocab)
    n = len(freqs)
    if n == 0:
        return [0.0, 0.0, 0.0, 0.0]
    return [freqs[max(0, n * i // 5)] for i in (1, 2, 3, 4)]
```

- [ ] **Step 4: Lancer les nouveaux tests**

Run: `python -m pytest tests/orquantix/test_vocabulary.py -q`
Expected: `8 passed`

- [ ] **Step 5: Retirer l'ancien fichier de tests et l'ancienne fonction**

`filter_eligible_words` n'existe plus. `tests/test_vocabulary.py` la teste et devient caduc — ses cas utiles sont déjà couverts par `tests/orquantix/test_vocabulary.py`.

```bash
git rm tests/test_vocabulary.py
```

Puis corriger l'appelant restant de `filter_eligible_words`, dans la fonction `_do_background_work` d'`app.py` (chercher `filter_eligible_words(` — les numéros de ligne ont bougé depuis la Task 2) :

```python
    pools = build_pools(str(lexique_path), model_vocab)
    vocab = pools.mystery_words
    freq_by_word = pools.mystery_freq
```

et l'import en tête de `app.py` :

```python
from games.orquantix.vocabulary import (
    build_norm_map,
    build_pools,
    compute_difficulty_thresholds,
    normalize,
)
```

- [ ] **Step 6: Vérifier toute la suite**

Run: `python -m pytest -q`
Expected: `57 passed` (46 − 10 de test_vocabulary + 8 nouveaux + 13 de dictionary)

Si un test de `test_app.py` échoue sur `state.norm_to_vocab`, le laisser tel quel pour l'instant : il sera traité en Task 8.

- [ ] **Step 7: Vérifier les tailles réelles des pools**

```bash
python - <<'PY'
from pathlib import Path
from games.orquantix.vocabulary import build_pools
from gensim.models import KeyedVectors

data = Path.home() / "Library" / "Application Support" / "Orquantix"
model = KeyedVectors.load_word2vec_format(str(data / "frWiki_no_phrase_no_postag_1000_skip_cut200.bin"), binary=True)
pools = build_pools(str(data / "Lexique383.tsv"), set(model.key_to_index))
print("mystères :", len(pools.mystery_words))
print("indices  :", len(pools.hint_words))
PY
```

Expected: `mystères : 2788` et `indices : 6916`

Ces deux nombres sont la validation de la Task 4. S'ils diffèrent, le filtre est faux.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: deux pools de vocabulaire distincts, mots mysteres restreints aux noms 10-400/M"
```

---

### Task 5: La température

Cœur de la refonte. Remplace `get_progress_percent`, dont la courbe renvoyait 0,00 % pour 96,7 % des mots proposables.

**Files:**
- Modify: `games/orquantix/engine.py`
- Test: `tests/orquantix/test_engine.py`

**Interfaces:**
- Consumes: rien
- Produces:
  - `@dataclass(frozen=True) class TemperatureScale` avec `floor: float`, `top1000: float`, `maximum: float`
  - `build_temperature_scale(model, target: str, neighbours: list[tuple[str, float]]) -> TemperatureScale`
  - `temperature(scale: TemperatureScale, similarity: float, *, found: bool = False) -> float`
  - `get_neighbours(model, target, topn=1000) -> list[tuple[str, float]]`
  - `get_top1000(model, target) -> dict[str, int]` — conservé
  - `get_daily_word`, `get_difficulty`, `get_score` — conservés

- [ ] **Step 1: Écrire les tests de la température**

Créer `tests/orquantix/test_engine.py` :

```python
import pytest

from games.orquantix.engine import (
    TemperatureScale,
    build_temperature_scale,
    temperature,
)

# Ancres réelles mesurées sur la cible "confiture".
SCALE = TemperatureScale(floor=0.0391, top1000=0.1551, maximum=0.7113)


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


class _FakeModel:
    """Modèle minimal : expose seulement ce que build_temperature_scale lit."""

    def __init__(self) -> None:
        self.key_to_index = {f"w{i}": i for i in range(1000)}

    def similarity(self, a: str, b: str) -> float:
        return 0.02
```

- [ ] **Step 2: Lancer pour voir échouer**

Run: `python -m pytest tests/orquantix/test_engine.py -q`
Expected: FAIL — `ImportError: cannot import name 'TemperatureScale'`

- [ ] **Step 3: Implémenter dans `games/orquantix/engine.py`**

Ajouter en tête du fichier (après les imports existants) :

```python
from dataclasses import dataclass

import numpy as np

FOUND_TEMPERATURE = 100.0
TOP1000_TEMPERATURE = 50.0
BEST_NEIGHBOUR_TEMPERATURE = 99.0


@dataclass(frozen=True)
class TemperatureScale:
    """Les trois ancres calibrant la température pour un mot mystère donné.

    Le seuil du top 1000 varie fortement d'une cible à l'autre — 0.155 pour
    « confiture », 0.196 pour « guerre » — donc une échelle fixe mentirait.
    """

    floor: float
    top1000: float
    maximum: float


def get_neighbours(model, target: str, topn: int = 1000) -> list[tuple[str, float]]:
    """Les voisins les plus proches, du plus proche au plus lointain."""
    limit = min(topn, len(model.key_to_index) - 1)
    return model.most_similar(target, topn=limit)


def build_temperature_scale(model, target: str, neighbours: list[tuple[str, float]]) -> TemperatureScale:
    """Calibre l'échelle sur la cible.

    Le plancher est la médiane des similarités de la cible contre tout le
    vocabulaire : 91 % des mots vivent sous 0.10, donc sans plancher la
    température serait écrasée en bas.
    """
    maximum = neighbours[0][1]
    top1000 = neighbours[-1][1]
    floor = _median_similarity(model, target)

    # Garde-fou : les ancres doivent rester strictement croissantes.
    if floor >= top1000:
        floor = top1000 * 0.25
    if top1000 >= maximum:
        top1000 = maximum * 0.5

    return TemperatureScale(floor=floor, top1000=top1000, maximum=maximum)


def _median_similarity(model, target: str) -> float:
    vectors = model.get_normed_vectors()
    target_vector = vectors[model.key_to_index[target]]
    similarities = vectors @ target_vector
    return float(np.median(similarities))


def temperature(scale: TemperatureScale, similarity: float, *, found: bool = False) -> float:
    """Similarité cosinus → degrés.

    0°   = aucun rapport
    50°  = entrée dans le top 1000
    99°  = le voisin le plus proche
    100° = trouvé
    """
    if found:
        return FOUND_TEMPERATURE

    if similarity <= scale.floor:
        return 0.0

    if similarity < scale.top1000:
        span = scale.top1000 - scale.floor
        return round(TOP1000_TEMPERATURE * (similarity - scale.floor) / span, 2)

    span = scale.maximum - scale.top1000
    if span <= 0:
        return BEST_NEIGHBOUR_TEMPERATURE

    climbed = (BEST_NEIGHBOUR_TEMPERATURE - TOP1000_TEMPERATURE) * (similarity - scale.top1000) / span
    return round(min(TOP1000_TEMPERATURE + climbed, BEST_NEIGHBOUR_TEMPERATURE), 2)
```

- [ ] **Step 4: Lancer les tests**

Run: `python -m pytest tests/orquantix/test_engine.py -q`
Expected: `9 passed`

Si `_median_similarity` échoue sur le `_FakeModel` (pas de `get_normed_vectors`), ajouter la méthode au fake plutôt que d'affaiblir le code :

```python
    def get_normed_vectors(self):
        import numpy as np
        return np.full((1000, 4), 0.02, dtype=np.float32)
```

- [ ] **Step 5: Supprimer l'ancienne courbe**

Retirer de `games/orquantix/engine.py` les fonctions `get_progress_percent` et `get_proximity_feedback` — elles seront remplacées en Task 6. Retirer aussi de `tests/test_game.py` les tests qui les visent :
`test_get_progress_percent_outside_top1000`, `test_get_progress_percent_inside_top1000`,
`test_get_proximity_feedback_for_ranked_guess`, `test_get_proximity_feedback_for_best_neighbor_caps_progress`,
`test_get_proximity_feedback_uses_shifted_left_thresholds`, `test_get_proximity_feedback_for_unknown_guess`,
`test_get_proximity_feedback_for_found_word`.

Ces tests ne sont pas perdus : leurs équivalents température existent déjà (Step 1) et les équivalents humeur arrivent en Task 6.

- [ ] **Step 6: Vérifier**

Run: `python -m pytest -q`
Expected: la suite est verte. `app.py` importe encore `get_proximity_feedback` — corriger l'import en le retirant, les routes seront réécrites en Task 8. En attendant, remplacer les appels par un dictionnaire minimal pour garder l'application importable :

```python
# Provisoire — remplacé en Task 8 par le blueprint.
def get_proximity_feedback(rank, found=False):
    return {"rank": rank, "found": found}
```

placé en haut de `app.py`, et retirer `get_proximity_feedback` de la liste d'imports.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: temperature continue calibree par cible, remplace la courbe morte"
```

---

### Task 6: Les humeurs de l'orque

Les humeurs s'indexent désormais sur la température et non plus sur le rang, et leurs seuils s'alignent sur le repère des 50°.

**Files:**
- Create: `games/orquantix/orca.py`
- Test: `tests/orquantix/test_orca.py`

**Interfaces:**
- Consumes: `games.orquantix.engine.temperature`
- Produces:
  - `mood_for(temperature: float, *, found: bool = False) -> str` → `"sick" | "vexed" | "intrigued" | "overexcited" | "solar" | "found"`
  - `beast_label(mood: str) -> str`
  - `proximity_label(mood: str) -> str`
  - `emoji(mood: str) -> str`
  - `rank_label(rank: int | None, *, found: bool = False) -> str`
  - `feedback(temperature: float, rank: int | None, *, found: bool = False) -> dict`

- [ ] **Step 1: Écrire les tests**

Créer `tests/orquantix/test_orca.py` :

```python
from games.orquantix.orca import beast_label, emoji, feedback, mood_for, rank_label


def test_mood_thresholds_at_the_boundaries():
    assert mood_for(0.0) == "sick"
    assert mood_for(19.99) == "sick"
    assert mood_for(20.0) == "vexed"
    assert mood_for(49.99) == "vexed"
    assert mood_for(50.0) == "intrigued"
    assert mood_for(69.99) == "intrigued"
    assert mood_for(70.0) == "overexcited"
    assert mood_for(87.99) == "overexcited"
    assert mood_for(88.0) == "solar"
    assert mood_for(99.99) == "solar"


def test_orca_becomes_intrigued_exactly_when_entering_top_1000():
    # 50° est le repère : c'est l'entrée dans le top 1000.
    assert mood_for(49.99) == "vexed"
    assert mood_for(50.0) == "intrigued"


def test_found_overrides_everything():
    assert mood_for(0.0, found=True) == "found"
    assert mood_for(100.0) == "found"


def test_measured_guesses_map_to_expected_moods():
    # Cible « confiture », températures mesurées.
    assert mood_for(96.0) == "solar"        # compote
    assert mood_for(76.0) == "overexcited"  # tartine
    assert mood_for(64.0) == "intrigued"    # cuisine
    assert mood_for(14.0) == "sick"         # bonjour
    assert mood_for(0.0) == "sick"          # moteur


def test_labels_exist_for_every_mood():
    for mood in ["sick", "vexed", "intrigued", "overexcited", "solar", "found"]:
        assert beast_label(mood)
        assert emoji(mood)


def test_rank_label_hides_rank_outside_top_1000():
    assert rank_label(None) == "Hors top 1000"
    assert rank_label(1500) == "Hors top 1000"
    assert rank_label(42) == "Voisin #42"
    assert rank_label(1, found=True) == "Mot mystère trouvé"


def test_feedback_bundles_everything_the_frontend_needs():
    result = feedback(76.0, 78)

    assert result["temperature"] == 76.0
    assert result["rank"] == 78
    assert result["mood"] == "overexcited"
    assert result["emoji"] == "🤯"
    assert result["rank_label"] == "Voisin #78"
    assert result["found"] is False


def test_feedback_for_a_word_outside_top_1000():
    result = feedback(14.0, None)

    assert result["rank"] is None
    assert result["rank_label"] == "Hors top 1000"
    assert result["mood"] == "sick"
```

- [ ] **Step 2: Lancer pour voir échouer**

Run: `python -m pytest tests/orquantix/test_orca.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'games.orquantix.orca'`

- [ ] **Step 3: Implémenter `games/orquantix/orca.py`**

```python
from __future__ import annotations

# Seuils alignés sur le repère des 50° = entrée dans le top 1000.
MOOD_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (20.0, "sick"),
    (50.0, "vexed"),
    (70.0, "intrigued"),
    (88.0, "overexcited"),
    (100.0, "solar"),
)

EMOJIS = {
    "sick": "🤢",
    "vexed": "😤",
    "intrigued": "🤨",
    "overexcited": "🤯",
    "solar": "☀️",
    "found": "☀️",
}

BEAST_LABELS = {
    "sick": "Malade",
    "vexed": "Vexé",
    "intrigued": "Intrigué",
    "overexcited": "Surexcité",
    "solar": "Solaire",
    "found": "Solaire",
}

PROXIMITY_LABELS = {
    "sick": "Très loin",
    "vexed": "L'orque est vexé",
    "intrigued": "L'orque s'intrigue",
    "overexcited": "L'orque s'emballe",
    "solar": "L'orque devient solaire",
    "found": "Trouvé",
}


def mood_for(temperature: float, *, found: bool = False) -> str:
    """Humeur de l'orque pour une température donnée."""
    if found or temperature >= 100.0:
        return "found"
    for ceiling, mood in MOOD_THRESHOLDS:
        if temperature < ceiling:
            return mood
    return "solar"


def emoji(mood: str) -> str:
    return EMOJIS[mood]


def beast_label(mood: str) -> str:
    return BEAST_LABELS[mood]


def proximity_label(mood: str) -> str:
    return PROXIMITY_LABELS[mood]


def rank_label(rank: int | None, *, found: bool = False) -> str:
    """Le rang n'existe qu'à l'intérieur du top 1000."""
    if found:
        return "Mot mystère trouvé"
    if rank is None or rank > 1000:
        return "Hors top 1000"
    return f"Voisin #{rank}"


def feedback(temperature: float, rank: int | None, *, found: bool = False) -> dict:
    """Tout ce dont le frontend a besoin pour afficher une ligne."""
    mood = mood_for(temperature, found=found)
    return {
        "temperature": temperature,
        "rank": rank if (rank is not None and rank <= 1000) else None,
        "mood": mood,
        "emoji": emoji(mood),
        "beast": beast_label(mood),
        "label": proximity_label(mood),
        "rank_label": rank_label(rank, found=found),
        "found": found,
    }
```

- [ ] **Step 4: Lancer les tests**

Run: `python -m pytest tests/orquantix/test_orca.py -q`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add games/orquantix/orca.py tests/orquantix/test_orca.py
git commit -m "feat: humeurs de l'orque indexees sur la temperature"
```

---

### Task 7: Les indices

Correction du bug central : les indices piochaient dans les 31 548 mots bruts du modèle. Et le poisson doré devient lecteur de dictionnaire.

**Files:**
- Create: `games/orquantix/hints.py`
- Test: `tests/orquantix/test_hints.py`

**Interfaces:**
- Consumes: `games.orquantix.dictionary.Littre`
- Produces:
  - `better_hint_word(top1000: dict[str, int], hint_words: frozenset[str], best_rank: int | None, guessed: set[str]) -> str | None`
  - `strong_hint_word(top1000, hint_words, guessed) -> str | None`
  - `golden_fish(target: str, littre, top1000, hint_words, guessed) -> dict` avec les clés `kind` (`"definition"` ou `"word"`), `message`, `value`

- [ ] **Step 1: Écrire les tests d'étanchéité — le test qui aurait attrapé le bug**

Créer `tests/orquantix/test_hints.py` :

```python
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
```

- [ ] **Step 2: Lancer pour voir échouer**

Run: `python -m pytest tests/orquantix/test_hints.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'games.orquantix.hints'`

- [ ] **Step 3: Implémenter `games/orquantix/hints.py`**

```python
from __future__ import annotations

STRONG_HINT_TIERS = (10, 25, 50, 100)


def _eligible(
    top1000: dict[str, int],
    hint_words: frozenset[str],
    guessed: set[str],
) -> list[tuple[str, int]]:
    """Voisins triés du plus proche au plus lointain, restreints au pool d'indices.

    C'est ici que se joue la correction du bug : sans ce filtre, le jeu peut
    proposer « des », « souvent » ou « jupiter ».
    """
    candidates = [
        (word, rank)
        for word, rank in top1000.items()
        if word in hint_words and word not in guessed
    ]
    candidates.sort(key=lambda item: item[1])
    return candidates


def strong_hint_word(
    top1000: dict[str, int],
    hint_words: frozenset[str],
    guessed: set[str],
) -> str | None:
    """Le meilleur voisin encore disponible, par paliers de proximité."""
    candidates = _eligible(top1000, hint_words, guessed)
    if not candidates:
        return None

    for ceiling in STRONG_HINT_TIERS:
        for word, rank in candidates:
            if rank <= ceiling:
                return word

    return candidates[0][0]


def better_hint_word(
    top1000: dict[str, int],
    hint_words: frozenset[str],
    best_rank: int | None,
    guessed: set[str],
) -> str | None:
    """Un voisin sensiblement meilleur que le meilleur coup actuel."""
    candidates = _eligible(top1000, hint_words, guessed)
    if not candidates:
        return None

    if best_rank is not None and best_rank <= 1:
        return None

    if best_rank is None or best_rank > 1000:
        target_rank = min(850, candidates[-1][1])
    else:
        step = max(1, best_rank // 5)
        target_rank = max(1, best_rank - step)

    better = [(w, r) for w, r in candidates if r <= target_rank]
    if not better and best_rank is not None:
        better = [(w, r) for w, r in candidates if r < best_rank]
    if not better:
        return None

    better.sort(key=lambda item: (abs(item[1] - target_rank), item[1]))
    return better[0][0]


def golden_fish(
    target: str,
    littre,
    top1000: dict[str, int],
    hint_words: frozenset[str],
    guessed: set[str],
) -> dict:
    """L'orque lit la définition du mot mystère.

    Pour les 74 mots du pool absents de Littré — tous modernes : avion,
    autobus, cinéma — on retombe sur le voisin fort.
    """
    definition = littre.lookup(target) if littre is not None else None

    if definition:
        return {
            "kind": "definition",
            "message": f"Le dictionnaire dit : « {definition} »",
            "value": definition,
        }

    word = strong_hint_word(top1000, hint_words, guessed)
    if word is None:
        return {
            "kind": "none",
            "message": "Le poisson doré n'a rien remonté de mieux.",
            "value": None,
        }

    return {
        "kind": "word",
        "message": f'Poisson doré : essaie "{word}"',
        "value": word,
    }
```

- [ ] **Step 4: Lancer les tests**

Run: `python -m pytest tests/orquantix/test_hints.py -q`
Expected: `10 passed`

- [ ] **Step 5: Retirer les anciennes fonctions d'indice**

Supprimer `get_better_hint_word` et `get_strong_hint_word` de `games/orquantix/engine.py`, ainsi que les tests correspondants dans `tests/test_game.py` (`test_get_better_hint_word_returns_closer_unused_candidate`, `test_get_better_hint_word_returns_none_for_best_rank`, `test_get_strong_hint_word_prefers_top_rank`). Retirer les imports devenus faux dans `app.py`.

- [ ] **Step 6: Vérifier**

Run: `python -m pytest -q`
Expected: suite verte

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "fix: les indices ne piochent plus que dans le pool d'indices; poisson dore lit Littre"
```

---

### Task 8: L'état isolé, le blueprint, et la coquille

Le gros du chantier structurel. `app.py` perd toute connaissance d'Orquantix.

**Files:**
- Create: `games/orquantix/state.py`, `games/orquantix/routes.py`
- Modify: `games/orquantix/__init__.py`, `app.py`, `tests/test_app.py` → `tests/orquantix/test_routes.py`

**Interfaces:**
- Consumes: tout ce qui précède
- Produces:
  - `OrquantixState` avec `.phase`, `.progress`, `.detail`, `.model`, `.pools`, `.scale`, `.top1000`, `.neighbours`, `.mystery_word`, `.difficulty`, `.game_index`, `.norm_to_model`, `.littre`, `.update(**kwargs)`
  - `games.orquantix.routes.build_blueprint(state) -> Blueprint` monté sur `/games/orquantix`
  - `games.orquantix.load_resources(state, data_dir)` — chargement paresseux

- [ ] **Step 1: Écrire `games/orquantix/state.py`**

```python
from __future__ import annotations

import threading

from games.orquantix.engine import TemperatureScale
from games.orquantix.vocabulary import Pools


class OrquantixState:
    """État d'Orquantix, isolé de la coquille.

    Vit côté serveur : c'est ce qui permet de quitter vers le menu et de
    retrouver sa partie en revenant.
    """

    def __init__(self) -> None:
        self.phase: str = "idle"  # idle | downloading | loading | ready | error
        self.progress: int = 0
        self.detail: str = ""
        self.model = None
        self.littre = None
        self.pools: Pools | None = None
        self.scale: TemperatureScale | None = None
        self.neighbours: list[tuple[str, float]] = []
        self.top1000: dict[str, int] = {}
        self.norm_to_model: dict[str, str] = {}
        self.difficulty_thresholds: list[float] = []
        self.mystery_word: str = ""
        self.difficulty: int = 0
        self.game_index: int = 0
        self.guesses: list[dict] = []
        self._lock = threading.Lock()

    def update(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                setattr(self, key, value)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "phase": self.phase,
                "progress": self.progress,
                "detail": self.detail,
            }
```

- [ ] **Step 2: Écrire les tests de routes**

Créer `tests/orquantix/test_routes.py` :

```python
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
```

- [ ] **Step 3: Lancer pour voir échouer**

Run: `python -m pytest tests/orquantix/test_routes.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'games.orquantix.routes'`

- [ ] **Step 4: Implémenter `games/orquantix/routes.py`**

```python
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from rapidfuzz import process as fuzz_process

from games.orquantix import engine, hints, orca
from games.orquantix.vocabulary import normalize

BLUEPRINT_NAME = "orquantix"
URL_PREFIX = "/games/orquantix"


def build_blueprint(state) -> Blueprint:
    bp = Blueprint(BLUEPRINT_NAME, __name__, url_prefix=URL_PREFIX)

    def _not_ready():
        return jsonify({"error": "not ready"}), 503

    def _record(word: str, temperature: float, rank: int | None, *, win: bool, gave_up: bool) -> dict:
        entry = orca.feedback(temperature, rank, found=win)
        entry.update({"word": word, "win": win, "gave_up": gave_up})
        state.guesses.append(entry)
        return entry

    @bp.route("/")
    def index():
        return render_template("orquantix/index.html")

    @bp.route("/status")
    def status():
        return jsonify(state.snapshot())

    @bp.route("/session")
    def session():
        return jsonify(
            {
                "difficulty": state.difficulty,
                "word_length": len(state.mystery_word),
                "guesses": state.guesses,
                "resolved": any(g["win"] for g in state.guesses),
            }
        )

    @bp.route("/guess", methods=["POST"])
    def guess():
        if state.phase != "ready":
            return _not_ready()

        payload = request.get_json(silent=True)
        if not payload or "word" not in payload:
            return jsonify({"error": "missing word"}), 400

        raw = str(payload["word"]).strip()
        norm = normalize(raw)

        if norm not in state.norm_to_model:
            return jsonify({"error": "inconnu"})

        word = state.norm_to_model[norm]

        if normalize(state.mystery_word) == norm:
            return jsonify(_record(state.mystery_word, 100.0, 1, win=True, gave_up=False))

        similarity = float(state.model.similarity(word, state.mystery_word))
        degrees = engine.temperature(state.scale, similarity)
        rank = state.top1000.get(word)
        return jsonify(_record(word, degrees, rank, win=False, gave_up=False))

    @bp.route("/give-up", methods=["POST"])
    def give_up():
        if state.phase != "ready":
            return _not_ready()
        return jsonify(_record(state.mystery_word, 100.0, 1, win=True, gave_up=True))

    @bp.route("/suggest", methods=["POST"])
    def suggest():
        if state.phase != "ready":
            return _not_ready()

        payload = request.get_json(silent=True)
        if not payload or "word" not in payload:
            return jsonify({"error": "missing word"}), 400

        match = fuzz_process.extractOne(
            normalize(str(payload["word"]).strip()),
            state.norm_to_model.keys(),
            score_cutoff=80,
        )
        if match is None:
            return jsonify({"suggestion": None})
        return jsonify({"suggestion": state.norm_to_model[match[0]]})

    @bp.route("/hint", methods=["POST"])
    def hint():
        if state.phase != "ready":
            return _not_ready()

        payload = request.get_json(silent=True) or {}
        kind = payload.get("type")
        if kind not in {"first-letter", "word-length", "better-word", "golden-fish"}:
            return jsonify({"error": "invalid hint type"}), 400

        if kind == "first-letter":
            letter = state.mystery_word[0]
            return jsonify({"type": kind, "message": f"Première lettre : {letter.upper()}", "value": letter})

        if kind == "word-length":
            length = len(state.mystery_word)
            return jsonify({"type": kind, "message": f"Nombre de lettres : {length}", "value": length})

        guessed = {g["word"] for g in state.guesses}
        pool = state.pools.hint_words

        if kind == "golden-fish":
            result = hints.golden_fish(state.mystery_word, state.littre, state.top1000, pool, guessed)
            return jsonify({"type": kind, **result})

        ranked = [g["rank"] for g in state.guesses if g["rank"] is not None]
        best_rank = min(ranked) if ranked else None
        word = hints.better_hint_word(state.top1000, pool, best_rank, guessed)
        if word is None:
            return jsonify(
                {"type": kind, "message": "Tu as déjà le meilleur indice possible.", "value": None}
            )
        return jsonify({"type": kind, "message": f'Essaie "{word}"', "value": word})

    @bp.route("/new-game", methods=["POST"])
    def new_game():
        if state.phase != "ready":
            return _not_ready()

        state.game_index += 1
        word = engine.get_daily_word(state.pools.mystery_words, state.game_index)
        neighbours = engine.get_neighbours(state.model, word)

        state.update(
            mystery_word=word,
            neighbours=neighbours,
            top1000={w: i + 1 for i, (w, _) in enumerate(neighbours)},
            scale=engine.build_temperature_scale(state.model, word, neighbours),
            difficulty=engine.get_difficulty(word, state.pools.mystery_freq, state.difficulty_thresholds),
            guesses=[],
        )
        return jsonify({"difficulty": state.difficulty, "word_length": len(word)})

    return bp
```

- [ ] **Step 5: Lancer les tests de routes**

Run: `python -m pytest tests/orquantix/test_routes.py -q`
Expected: `9 passed`

Le test `index()` peut échouer faute de template : il n'est pas dans la liste, ne pas s'en inquiéter avant la Task 10.

- [ ] **Step 6: Écrire le chargeur dans `games/orquantix/__init__.py`**

```python
from __future__ import annotations

from pathlib import Path

from games.orquantix import engine
from games.orquantix.dictionary import DICT_FILENAME, IDX_FILENAME, Littre
from games.orquantix.routes import build_blueprint
from games.orquantix.state import OrquantixState
from games.orquantix.vocabulary import (
    build_norm_map,
    build_pools,
    compute_difficulty_thresholds,
)

GAME_ID = "orquantix"
GAME_NAME = "Orquantix"
MODEL_FILENAME = "frWiki_no_phrase_no_postag_1000_skip_cut200.bin"
LEXIQUE_FILENAME = "Lexique383.tsv"

__all__ = ["GAME_ID", "GAME_NAME", "OrquantixState", "build_blueprint", "load_resources"]


def load_resources(state: OrquantixState, data_dir: Path) -> None:
    """Charge le modèle, les pools et le dictionnaire.

    Déclenché à l'entrée dans le jeu, pas au démarrage de l'application :
    un quiz géographique n'a aucun usage d'un modèle Word2Vec de 126 Mo.
    """
    from gensim.models import KeyedVectors

    state.update(phase="loading", progress=0, detail="Chargement du modèle Word2Vec…")
    model = KeyedVectors.load_word2vec_format(str(data_dir / MODEL_FILENAME), binary=True)

    state.update(progress=60, detail="Filtrage du vocabulaire…")
    pools = build_pools(str(data_dir / LEXIQUE_FILENAME), set(model.key_to_index))
    if not pools.mystery_words:
        raise RuntimeError("Aucun mot éligible — vérifier Lexique383.tsv")

    state.update(progress=75, detail="Ouverture du dictionnaire…")
    try:
        littre = Littre(data_dir / IDX_FILENAME, data_dir / DICT_FILENAME)
    except (OSError, ValueError):
        littre = None  # le poisson doré retombera sur le voisin fort

    state.update(progress=85, detail="Tirage du mot mystère…")
    word = engine.get_daily_word(pools.mystery_words, state.game_index)
    neighbours = engine.get_neighbours(model, word)
    thresholds = compute_difficulty_thresholds(pools.mystery_words, pools.mystery_freq)

    state.update(
        model=model,
        littre=littre,
        pools=pools,
        norm_to_model=build_norm_map(list(model.key_to_index)),
        difficulty_thresholds=thresholds,
        mystery_word=word,
        neighbours=neighbours,
        top1000={w: i + 1 for i, (w, _) in enumerate(neighbours)},
        scale=engine.build_temperature_scale(model, word, neighbours),
        difficulty=engine.get_difficulty(word, pools.mystery_freq, thresholds),
        guesses=[],
        phase="ready",
        progress=100,
        detail="Prêt !",
    )
```

- [ ] **Step 7a: Ajouter `missing_files` à `downloader.py`**

La coquille écrite au step suivant en dépend. La Task 9 raffinera cette fonction quand les trois fichiers seront déclarés ; pour l'instant elle s'appuie sur les deux constantes existantes.

```python
def missing_files(data_dir) -> list[str]:
    """Les fichiers requis qui ne sont pas encore sur le disque."""
    required = (LEXIQUE_FILENAME, MODEL_FILENAME)
    return [name for name in required if not (data_dir / name).exists()]
```

- [ ] **Step 7b: Réécrire `app.py` en coquille**

Remplacer intégralement :

```python
from __future__ import annotations

import os
import threading
from pathlib import Path

from flask import Flask, jsonify, redirect, url_for

from downloader import download_all, missing_files
from games.orquantix import GAME_ID, OrquantixState, build_blueprint, load_resources

APP_NAME = "PROCRASTINATOR"


class Shell:
    """L'application. Ne connaît aucune règle de mini-jeu."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.orquantix = OrquantixState()
        self._started: set[str] = set()
        self._lock = threading.Lock()

    def ensure_loaded(self, game_id: str) -> None:
        """Déclenche le chargement d'un jeu, une seule fois."""
        with self._lock:
            if game_id in self._started:
                return
            self._started.add(game_id)

        thread = threading.Thread(
            target=self._load, args=(game_id,), daemon=True
        )
        thread.start()

    def _load(self, game_id: str) -> None:
        state = self.orquantix
        try:
            if missing_files(self.data_dir):
                state.update(phase="downloading", progress=0, detail="Téléchargement…")
                download_all(state, self.data_dir)
            load_resources(state, self.data_dir)
        except Exception as exc:  # noqa: BLE001 — remonté à l'écran de chargement
            state.update(phase="error", detail=f"Erreur : {exc}")


def create_app(shell: Shell) -> Flask:
    templates_dir = os.environ.get("PROCRASTINATOR_TEMPLATES", "templates")
    static_dir = os.environ.get("PROCRASTINATOR_STATIC", "static")
    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    app.register_blueprint(build_blueprint(shell.orquantix))

    @app.route("/")
    def home():
        # Phase 2 : le menu de PROCRASTINATOR. En attendant, on entre dans le jeu.
        shell.ensure_loaded(GAME_ID)
        return redirect(url_for("orquantix.index"))

    @app.route("/status")
    def status():
        return jsonify(shell.orquantix.snapshot())

    return app
```

- [ ] **Step 8: Migrer `tests/test_app.py`**

Ce fichier teste l'ancien `AppState` monolithique. Ses cas utiles sont repris dans `tests/orquantix/test_routes.py`.

```bash
git rm tests/test_app.py tests/test_game.py
```

Les cas restants de `test_game.py` (`get_daily_word`, `get_difficulty`, `get_score`, `get_top1000`) sont à recopier dans `tests/orquantix/test_engine.py` avant suppression — ne pas perdre de couverture. Vérifier avec :

Run: `python -m pytest -q --collect-only | tail -3`
Expected: le total de tests collectés ne doit pas baisser de plus de ce qui a été explicitement remplacé.

- [ ] **Step 9: Vérifier**

Run: `python -m pytest -q`
Expected: suite verte

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "refactor: Orquantix en blueprint isole, app.py devient la coquille PROCRASTINATOR"
```

---

### Task 9: Le téléchargeur à trois fichiers et la migration du dossier de données

Sans migration du dossier, chaque utilisateur retélécharge environ 180 Mo.

**Files:**
- Modify: `downloader.py`, `main.py`
- Test: `tests/test_downloader.py`

**Interfaces:**
- Consumes: rien
- Produces:
  - `missing_files(data_dir: Path) -> list[str]`
  - `download_all(state, data_dir)` — trois fichiers
  - `main.get_data_dir() -> Path` — migre `Semantix` puis `Orquantix` vers `Procrastinator`

- [ ] **Step 1: Écrire les tests de migration**

Créer `tests/test_downloader.py` :

```python
from pathlib import Path

import main
from downloader import DOWNLOADS, missing_files


def test_three_files_are_declared():
    names = {spec.filename for spec in DOWNLOADS}

    assert "Lexique383.tsv" in names
    assert "frWiki_no_phrase_no_postag_1000_skip_cut200.bin" in names
    assert "XMLittre.dict.dz" in names


def test_download_shares_sum_to_one_hundred():
    assert sum(spec.share for spec in DOWNLOADS) == 100


def test_missing_files_lists_absent_ones(tmp_path):
    (tmp_path / "Lexique383.tsv").write_text("x")

    missing = missing_files(tmp_path)

    assert "Lexique383.tsv" not in missing
    assert "frWiki_no_phrase_no_postag_1000_skip_cut200.bin" in missing


def test_data_dir_migrates_orquantix_to_procrastinator(tmp_path, monkeypatch):
    support = tmp_path / "Library" / "Application Support"
    legacy = support / "Orquantix"
    legacy.mkdir(parents=True)
    (legacy / "Lexique383.tsv").write_text("données")

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    result = main.get_data_dir()

    assert result.name == "Procrastinator"
    assert (result / "Lexique383.tsv").read_text() == "données"
    assert not legacy.exists()


def test_data_dir_prefers_existing_procrastinator(tmp_path, monkeypatch):
    support = tmp_path / "Library" / "Application Support"
    (support / "Procrastinator").mkdir(parents=True)
    (support / "Orquantix").mkdir(parents=True)

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    assert main.get_data_dir().name == "Procrastinator"
```

- [ ] **Step 2: Lancer pour voir échouer**

Run: `python -m pytest tests/test_downloader.py -q`
Expected: FAIL — `ImportError: cannot import name 'DOWNLOADS'`

- [ ] **Step 3: Réécrire la déclaration des téléchargements dans `downloader.py`**

Remplacer les constantes de tête par :

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Download:
    url: str
    filename: str
    share: int  # part de la barre de progression globale


DOWNLOADS: tuple[Download, ...] = (
    Download(
        url="http://www.lexique.org/databases/Lexique383/Lexique383.tsv",
        filename="Lexique383.tsv",
        share=14,
    ),
    Download(
        url="https://embeddings.net/embeddings/frWiki_no_phrase_no_postag_1000_skip_cut200.bin",
        filename="frWiki_no_phrase_no_postag_1000_skip_cut200.bin",
        share=70,
    ),
    Download(
        url="https://archive.org/download/XMLittre.dict/XMLittre.dict.dz",
        filename="XMLittre.dict.dz",
        share=15,
    ),
    Download(
        url="https://archive.org/download/XMLittre.dict/XMLittre.idx",
        filename="XMLittre.idx",
        share=1,
    ),
)

LEXIQUE_FILENAME = DOWNLOADS[0].filename
MODEL_FILENAME = DOWNLOADS[1].filename


def missing_files(data_dir) -> list[str]:
    """Les fichiers déclarés qui ne sont pas encore sur le disque."""
    return [spec.filename for spec in DOWNLOADS if not (data_dir / spec.filename).exists()]
```

**Les URL Littré sont vérifiées** (2026-08-16) : les deux répondent en HTTP 200 avec `content-length` 29 654 881 et 2 358 585 octets, exactement les tailles des fichiers déjà présents localement. Le dictionnaire compte donc **quatre** entrées dans `DOWNLOADS`, puisque l'index et le corps sont deux fichiers distincts et tous deux nécessaires.

Adapter `test_three_files_are_declared` en conséquence — il doit vérifier la présence des quatre noms de fichiers, `XMLittre.idx` compris.

Attribution à porter dans le README : texte d'Émile Littré, domaine public ; encodage XML par François Gannaz (https://littre.org), CC-BY-SA 3.0.

- [ ] **Step 4: Réécrire `download_all`**

```python
def download_all(state, data_dir: Path) -> None:
    """Télécharge les fichiers manquants, en répartissant la progression."""

    def on_progress(pct: int, detail: str) -> None:
        state.update(progress=pct, detail=detail)

    start = 0
    for spec in DOWNLOADS:
        end = start + spec.share
        destination = data_dir / spec.filename
        if not destination.exists():
            on_progress(start, f"Téléchargement de {spec.filename}…")
            download_file(spec.url, destination, on_progress, start, end)
        start = end

    on_progress(100, "Téléchargement terminé.")
```

- [ ] **Step 5: Réécrire `get_data_dir` dans `main.py`**

```python
def get_data_dir() -> Path:
    """Dossier de données, en migrant les noms historiques.

    Sans cette migration, renommer l'application ferait retélécharger
    environ 180 Mo à chaque utilisateur.
    """
    support = Path.home() / "Library" / "Application Support"
    preferred = support / "Procrastinator"
    legacy_names = ("Orquantix", "Semantix")

    if preferred.exists():
        return preferred

    for name in legacy_names:
        legacy = support / name
        if legacy.exists():
            try:
                legacy.rename(preferred)
                return preferred
            except OSError:
                return legacy

    return preferred
```

- [ ] **Step 6: Adapter `main()` à la coquille**

Dans `main.py`, remplacer le bloc de démarrage :

```python
    from app import Shell, create_app

    shell = Shell(data_dir)
    flask_app = create_app(shell)
```

et retirer l'appel à `start_background`, désormais déclenché par la route `/`. Changer aussi le titre de la fenêtre et les variables d'environnement :

```python
        os.environ["PROCRASTINATOR_TEMPLATES"] = str(base / "templates")
        os.environ["PROCRASTINATOR_STATIC"] = str(base / "static")
```

```python
        window = webview.create_window(
            title="PROCRASTINATOR",
            url=url,
            width=720,
            height=900,
            resizable=True,
            min_size=(480, 600),
        )
```

- [ ] **Step 7: Vérifier**

Run: `python -m pytest -q`
Expected: suite verte

Run: `grep -rn "SEMANTIX" app.py main.py`
Expected: aucune sortie

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: telechargeur a trois fichiers et migration du dossier de donnees vers Procrastinator"
```

---

### Task 10: Le frontend

Découpage des 909 lignes d'`index.html` et passage au tableau à deux colonnes distinctes.

**Files:**
- Create: `templates/orquantix/index.html`, `static/shell.css`, `static/orquantix/style.css`, `static/orquantix/game.js`, `static/orquantix/orca.js`
- Delete: `templates/index.html`, `static/style.css`

**Interfaces:**
- Consumes: les routes `/games/orquantix/*`
- Produces: l'interface de jeu

- [ ] **Step 1: Créer l'arborescence et déplacer le CSS**

```bash
mkdir -p templates/orquantix static/orquantix
git mv static/style.css static/orquantix/style.css
git mv templates/index.html templates/orquantix/index.html
```

- [ ] **Step 2: Extraire les tokens partagés dans `static/shell.css`**

```css
/* Tokens partagés par PROCRASTINATOR et tous ses mini-jeux. */
:root {
  --bg: #faf9f7;
  --fg: #1c1b19;
  --muted: #6b6a67;
  --line: rgba(28, 27, 25, 0.14);
  --accent: #4a90e2;

  --temp-cold: #8b9bb4;
  --temp-cool: #e5c33c;
  --temp-warm: #e8913f;
  --temp-hot: #e0554e;

  --radius: 9px;
  --gap: 12px;
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

body {
  margin: 0;
  padding: 24px;
  background: var(--bg);
  color: var(--fg);
  font-family: var(--font);
}

.tile {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px;
  text-align: center;
  font-weight: 600;
  cursor: pointer;
}

.tile:hover { background: rgba(0, 0, 0, 0.03); }
```

Puis, dans `templates/orquantix/index.html`, référencer les deux feuilles :

```html
  <link rel="stylesheet" href="/static/shell.css">
  <link rel="stylesheet" href="/static/orquantix/style.css">
```

- [ ] **Step 3: Extraire le JavaScript**

Déplacer le contenu du `<script>` de `templates/orquantix/index.html` (lignes 151-907 du fichier d'origine) vers deux fichiers :

- `static/orquantix/orca.js` — les constantes `ORCA_TOOLS`, `ORCA_MASCOTS`, `ORCA_LINES`, `PROXIMITY_ICONS`, et les fonctions `setOrcaState`, `speakOrca`, `syncOrcaTools`, `applyOrcaTool`, `initOrcaDragAndDrop`, `toggleDyslexic`, `triggerEasterEgg`, `buildKefirRain`
- `static/orquantix/game.js` — tout le reste : `submitGuess`, `submitWord`, `giveUp`, `renderTable`, `newGame`, `requestHint`, le timer, les suggestions

Remplacer le bloc `<script>` par :

```html
  <script src="/static/orquantix/orca.js"></script>
  <script src="/static/orquantix/game.js"></script>
```

Vérifier qu'il ne reste aucun script inline :

Run: `grep -c "<script>" templates/orquantix/index.html`
Expected: `0`

- [ ] **Step 4: Adapter les appels réseau au préfixe du blueprint**

Dans `static/orquantix/game.js`, remplacer toutes les URL :

| Avant | Après |
|---|---|
| `fetch('/guess'` | `fetch('/games/orquantix/guess'` |
| `fetch('/give-up'` | `fetch('/games/orquantix/give-up'` |
| `fetch('/suggest'` | `fetch('/games/orquantix/suggest'` |
| `fetch('/hint'` | `fetch('/games/orquantix/hint'` |
| `fetch('/new-game'` | `fetch('/games/orquantix/new-game'` |
| `fetch('/status')` | `fetch('/games/orquantix/status')` |
| `fetch('/daily-info')` | `fetch('/games/orquantix/session')` |

Run: `grep -n "fetch('/[a-z]" static/orquantix/game.js`
Expected: aucune sortie — toutes les URL sont préfixées

- [ ] **Step 5: Passer le tableau à deux colonnes distinctes**

Dans `templates/orquantix/index.html`, remplacer l'en-tête du tableau :

```html
      <thead>
        <tr>
          <th class="col-num">#</th>
          <th class="col-word">Mot</th>
          <th class="col-temperature">Température</th>
          <th class="col-rank">Rang</th>
          <th class="col-orca">Orque</th>
        </tr>
      </thead>
```

Dans `static/orquantix/game.js`, remplacer `renderTable` :

```javascript
function renderTable() {
  const tbody = document.getElementById('guessTableBody');
  const animations = [];
  tbody.innerHTML = '';

  for (const g of guesses) {
    const tr = document.createElement('tr');
    const shouldAnimate = g.temperatureAnimated !== true;
    const shown = shouldAnimate ? 0 : g.temperature;

    tr.className = 'guess-row orca-' + g.mood;
    tr.innerHTML =
      '<td class="guess-number">' + g.attempt + '</td>' +
      '<td class="guess-word">' + esc(g.word) + '</td>' +
      '<td class="guess-temperature">' +
        '<div class="temperature-row">' +
          '<span class="temperature-value">' + Math.round(shown) + '°</span>' +
          '<div class="temperature-bar">' +
            '<div class="temperature-bar-fill" style="width:' + shown + '%"></div>' +
          '</div>' +
        '</div>' +
      '</td>' +
      '<td class="guess-rank">' +
        (g.rank ? '<span class="rank-badge">#' + g.rank + '</span>' : '<span class="rank-none">—</span>') +
      '</td>' +
      '<td class="guess-orca">' +
        '<img class="orca-emoji" src="' + esc(PROXIMITY_ICONS[g.mood] || PROXIMITY_ICONS.sick) +
        '" alt="' + esc(g.label) + '" title="' + esc(g.label) + '">' +
      '</td>';

    tbody.appendChild(tr);
    if (shouldAnimate) animations.push(animateTemperature(tr, g));
  }

  return Promise.all(animations);
}
```

- [ ] **Step 6: Adapter l'animation et le tri**

Remplacer `animateProgressReveal` par `animateTemperature` — même mécanique, nouvelles clés :

```javascript
function animateTemperature(row, guess) {
  const valueEl = row.querySelector('.temperature-value');
  const fillEl = row.querySelector('.temperature-bar-fill');
  const target = Math.max(0, Math.min(100, Number(guess.temperature) || 0));

  guess.temperatureAnimated = true;

  if (!valueEl || !fillEl || target <= 0) {
    if (valueEl) valueEl.textContent = Math.round(target) + '°';
    if (fillEl) fillEl.style.width = target + '%';
    return Promise.resolve();
  }

  fillEl.classList.add('is-animating');

  return new Promise(resolve => {
    const duration = Math.min(2200, 520 + target * 12);
    const start = performance.now();

    function step(now) {
      const ratio = Math.min((now - start) / duration, 1);
      const current = target * ratio;
      fillEl.style.width = current + '%';
      valueEl.textContent = Math.round(current) + '°';

      if (ratio < 1) { requestAnimationFrame(step); return; }

      fillEl.classList.remove('is-animating');
      fillEl.style.width = target + '%';
      valueEl.textContent = Math.round(target) + '°';
      resolve();
    }

    requestAnimationFrame(step);
  });
}
```

Et le tri, partout où il apparaît (`submitWord`, `giveUp`) :

```javascript
  guesses.sort((a, b) => b.temperature - a.temperature);
```

- [ ] **Step 7: Restaurer la partie en cours au chargement**

C'est ce qui rend le retour au menu non destructif. Dans `game.js`, remplacer l'appel à `/daily-info` de `activateGame` :

```javascript
function activateGame() {
  document.getElementById('downloadScreen').style.display = 'none';
  document.getElementById('gameScreen').style.display = 'block';

  fetch('/games/orquantix/session')
    .then(r => r.json())
    .then(data => {
      renderDifficulty(data.difficulty);
      guesses = data.guesses.map((g, i) => ({...g, attempt: i + 1, temperatureAnimated: true}));
      guessCounter = guesses.length;
      guesses.sort((a, b) => b.temperature - a.temperature);
      renderTable();
      if (data.resolved) showVictory();
    });

  document.getElementById('guessInput').focus();
  document.body.classList.toggle('dyslexic-mode', dyslexicMode);
  resetTimer();
  applyOrcaTool(orcaMode, 'Ola que tal');
}
```

- [ ] **Step 8: Ajouter le CSS des nouvelles colonnes**

Ajouter à `static/orquantix/style.css` :

```css
/* ===== Colonnes température et rang ===== */
.guess-temperature { min-width: 190px; }

.temperature-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.temperature-value {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  min-width: 38px;
}

.temperature-bar {
  flex: 1;
  height: 8px;
  border-radius: 99px;
  background: rgba(128, 128, 128, 0.18);
  overflow: hidden;
}

.temperature-bar-fill {
  height: 100%;
  border-radius: 99px;
  transition: width 0.2s ease;
}

.orca-sick .temperature-bar-fill,
.orca-vexed .temperature-bar-fill { background: var(--temp-cold); }
.orca-intrigued .temperature-bar-fill { background: var(--temp-cool); }
.orca-overexcited .temperature-bar-fill { background: var(--temp-warm); }
.orca-solar .temperature-bar-fill,
.orca-found .temperature-bar-fill { background: var(--temp-hot); }

.rank-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 99px;
  font-size: 0.78rem;
  font-weight: 700;
  background: #f0c14b;
  color: #3a2c00;
}

.rank-none { opacity: 0.3; }
```

Supprimer les anciennes règles `.guess-proximity`, `.proximity-*` et `.guess-score` devenues mortes.

- [ ] **Step 9: Lancer l'application et vérifier à l'œil**

```bash
source .venv/bin/activate
python main.py --design
```

Vérifier dans le navigateur, dans cet ordre :

1. Le chargement démarre et la barre progresse
2. Proposer `moteur` → 0°, rang `—`, orque malade
3. Proposer `bonjour` → une température non nulle, rang `—`. **C'est la validation de toute la refonte** : deux mots faux, deux températures différentes
4. Proposer un mot proche → température élevée et un rang `#N` apparaît
5. Cliquer le poisson doré → une définition s'affiche, sans parenthèse phonétique, sans le mot mystère
6. Recharger la page → la partie est toujours là

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: frontend decoupe, tableau temperature et rang en colonnes distinctes"
```

---

### Task 11: Renommage PROCRASTINATOR, packaging et README

**Files:**
- Create: `PROCRASTINATOR.spec` (via build.sh)
- Delete: `Semantix.spec`, `Orquantix.spec`
- Modify: `build.sh`, `README.md`

**Interfaces:**
- Consumes: tout ce qui précède
- Produces: un `.app` nommé PROCRASTINATOR

- [ ] **Step 1: Supprimer les fichiers `.spec` obsolètes**

```bash
git rm Semantix.spec Orquantix.spec
```

Ils sont régénérés par PyInstaller à chaque build ; les garder en dépôt n'apporte rien et `Semantix.spec` est un vestige.

- [ ] **Step 2: Adapter `build.sh`**

```bash
VENV=".venv_build"
APP="PROCRASTINATOR"
ICON="build_assets/Orquantix.icns"
```

et ajouter le paquet des jeux aux données embarquées :

```bash
pyinstaller \
  --noconfirm \
  --onedir \
  --windowed \
  --name "$APP" \
  --icon "$ICON" \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --collect-all gensim \
  --collect-all scipy \
  --hidden-import "gensim.models.keyedvectors" \
  --hidden-import "gensim.models.word2vec" \
  --hidden-import "scipy.sparse.csgraph._validation" \
  --collect-all pywebview \
  --hidden-import "webview" \
  main.py
```

**Note :** l'icône reste `Orquantix.icns` tant qu'aucune icône PROCRASTINATOR n'existe. Ne pas inventer de fichier absent.

- [ ] **Step 3: Écrire le README**

Le dépôt ne documente aujourd'hui aucune procédure de lancement, alors que l'objectif est que n'importe qui puisse cloner et jouer.

```markdown
# PROCRASTINATOR

Une petite application macOS regroupant des mini-jeux. Le premier est
**Orquantix**, un jeu de proximité sémantique en français.

## Jouer depuis les sources

```bash
git clone https://github.com/maverest/Orquantix.git
cd Orquantix
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Au premier lancement, l'application télécharge ses ressources — Lexique383,
un modèle Word2Vec français et le dictionnaire Littré, environ 180 Mo au
total — dans `~/Library/Application Support/Procrastinator/`. Les lancements
suivants sont immédiats.

`python main.py --design` ouvre l'interface dans le navigateur par défaut
plutôt que dans la fenêtre native, ce qui donne accès aux outils de
développement.

## Construire l'application

```bash
./build.sh
```

Produit `dist/PROCRASTINATOR.app`.

## Tests

```bash
source .venv/bin/activate
python -m pytest
```

## Orquantix

Trouver le mot mystère — toujours un nom commun — en proposant des mots.
Chaque proposition reçoit une **température** de 0 à 100 : 50° signifie que
le mot fait partie des mille plus proches voisins du mot mystère, et son
**rang** apparaît alors. L'orque commente.
```

- [ ] **Step 4: Vérifier qu'il ne reste aucune trace des anciens noms**

Run: `grep -rn "Semantix\|SEMANTIX" --include="*.py" --include="*.sh" --include="*.md" --include="*.html" . | grep -v docs/superpowers | grep -v "\.venv"`
Expected: aucune sortie

- [ ] **Step 5: Lancer la suite complète**

Run: `python -m pytest -q`
Expected: suite verte

- [ ] **Step 6: Construire et lancer le `.app`**

```bash
./build.sh
open dist/PROCRASTINATOR.app
```

Vérifier que la fenêtre s'intitule PROCRASTINATOR et que le jeu démarre sans retélécharger les 180 Mo — c'est le test de la migration du dossier de données.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: renommage PROCRASTINATOR, packaging et README d'installation"
```

---

## Notes pour l'implémenteur

**Trois pièges répertoriés, à ne pas redécouvrir :**

1. **La transcription phonétique de Littré épelle le mot.** `(kon-fi-tu-r')` en tête de l'entrée « confiture ». Si le nettoyage la laisse passer, le poisson doré ne donne plus un indice mais la réponse. Le test `test_clean_definition_strips_phonetic_prefix` est le garde-fou.

2. **Le pool d'indices n'est pas le pool de mots mystères.** Le premier est plus large — il contient verbes et adjectifs. Confondre les deux ferait perdre `confire` comme indice pour « confiture ». Le test `test_hints_never_return_a_word_outside_the_hint_pool` couvre le sens inverse, celui du bug d'origine.

3. **Renommer le dossier de données sans migration coûte 180 Mo à chaque utilisateur.** `main.get_data_dir` doit gérer les deux noms historiques, `Orquantix` et `Semantix`.

**Deux points à vérifier avant de committer, jamais à inventer :**

- L'URL de téléchargement de Littré (Task 9, Step 3). Le fichier est déjà présent localement ; si aucune URL stable n'existe, rendre le dictionnaire optionnel plutôt que de coder une adresse qui ne répond pas.
- Le nombre exact de tests après chaque suppression de fichier de test. Les cas utiles de `test_game.py` et `test_app.py` doivent être recopiés avant suppression, pas perdus.

**Hors périmètre, à ne pas commencer :** le menu de PROCRASTINATOR, les autres mini-jeux, et la réécriture de l'historique git pour purger les 130 Mo de `dist/`.
