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


_TAG = re.compile(r"<[^>]+>")


def _detag(text: str) -> str:
    """Retire tout le balisage, sans laisser une balise supprimée souder
    deux mots (ex. "<variante ...>" entre deux résumés de sens consécutifs,
    "rase.<variante...>Planche" -> "rase.Planche").

    Une espace n'est insérée qu'au point de coupure précis où c'est
    nécessaire : quand le caractère qui suivait immédiatement la balise est
    alphanumérique (donc amorce un mot) ET que le caractère qui précédait la
    balise n'est ni vide ni déjà une espace. Une balise directement suivie
    de ponctuation (ex. "mot</b>, RAC." où le "," suit la balise) n'est,
    elle, jamais transformée en espace : le remplacement inconditionnel par
    une espace créerait sinon une espace parasite avant cette ponctuation
    ("mot , RAC.") — un défaut mesuré sur plus de la moitié du vrai
    vocabulaire mystère lors d'un premier essai moins ciblé, à cause des
    citations Littré qui referment une balise juste avant leur virgule de
    référence.
    """

    def replace(match: re.Match[str]) -> str:
        start, end = match.start(), match.end()
        before = text[start - 1] if start > 0 else ""
        after = text[end] if end < len(text) else ""
        if after.isalnum() and before and not before.isspace():
            return " "
        return ""

    return _TAG.sub(replace, text)


_LEADING_PARENS = re.compile(r"^\s*\([^)]*\)\s*")
_GRAMMAR_MARKER = re.compile(
    r"^\s*(s\.\s*[mf]\.(\s*et\s*f\.)?(\s*pl\.)?|adj\.|v\.\s*[an]\.|v\.\s*(tr|intr|réfl|pron)\.|"
    r"adv\.|prép\.|conj\.|interj\.|pron\.|part\.|loc\.\s*adv\.)\s*",
    re.IGNORECASE,
)
# Jonction entre deux groupes chaînés en tête d'entrée, ex. les entrées à
# double genre : "(le mâle), s. f. (la femelle)" — la virgule qui sépare
# les deux groupes bloque sinon les regex ancrées suivantes.
_LEADING_JUNCTION = re.compile(r"^\s*[,;]\s*")
# Marqueur de sens en tête ("1°", "2°" pour le corps du dictionnaire, "2."
# pour les entrées de supplément qui reprennent leur propre numérotation).
_LEADING_SENSE = re.compile(r"^\s*\d+[°.]\s*")
# Connecteur avant une variante orthographique/de genre placée en tête :
# "ou ESCARBITE (...)", "Ou COPALE (...)", "au plur. SOUPIRAUX (...)",
# "au pluriel YEOMEN (...)".
_LEADING_CONNECTIVE = re.compile(r"^\s*(ou|au\s+plur(?:\.|iel\.?)?)\s+", re.IGNORECASE)
# Mot-vedette alternatif tout en capitales (variante, pluriel irrégulier,
# bannière de supplément) suivi éventuellement de sa parenthèse phonétique :
# "OGRESSE (o-grè-s')", "YEOMEN (iomèn)", "SUPPLÉMENT", "AU", "DICTIONNAIRE".
# Un mot normal ne s'écrit jamais tout en capitales en tête d'une définition
# Littré (seule l'initiale est majuscule) : ce motif est donc un signal
# structurel fiable, pas une coïncidence de casse.
_LEADING_ALT_HEADWORD = re.compile(
    r"^\s*[A-ZÀ-ÜŒÆÇ][A-ZÀ-ÜŒÆÇ\-]+(?![a-zà-ÿœæç])\s*(?:\([^)]*\))?\s*"
)
_SECOND_SENSE = re.compile(r"\s*2°")
# Citation Littré : ", AUTEUR" suivi soit d'un point d'abréviation
# ("CHATEAUBR."), soit directement de la référence ("BUFFON, Chat..",
# nom complet non abrégé) — jusqu'au(x) point(s) qui la terminent.
_CITATION = re.compile(r",\s*[A-ZÀ-Ý]{4,}\.?(?:,\s*[^.]*)?\.+")
_WHITESPACE = re.compile(r"\s+")

# Filet de sécurité indépendant : une transcription phonétique Littré a une
# forme reconnaissable — des syllabes en minuscules séparées par des traits
# d'union, parfois terminées par une apostrophe — où qu'elle apparaisse dans
# le texte, pas seulement en tête. Le trait d'union est exigé (au moins deux
# syllabes) pour ne pas confondre avec une note d'usage courte et légitime
# comme "(rare)" ou "(fig.)", qui n'a pas cette forme. Ce filet rattrape les
# fuites internes (ex. une bannière de supplément au milieu du texte) que le
# nettoyeur de tête, par construction, ne peut pas voir.
_PHONETIC_PAREN = re.compile(r"\([a-zà-ÿœæç]+(?:-[a-zà-ÿœæç]+)+'?\)")

# Bannières d'appendice Littré : ÉTYMOLOGIE, HISTORIQUE, SUPPLÉMENT AU
# DICTIONNAIRE, REMARQUE(S), SYNONYME, PROVERBE(S). Dans les 93 313 entrées
# de l'index réel, la balise <big>...</big> ne sert JAMAIS à autre chose que
# ces sept libellés (86 334 occurrences vérifiées, aucune variante), et
# aucune entrée ne commence par elle : la définition utile la précède
# toujours. On coupe donc dessus — plutôt que d'exciser juste le libellé —
# avant même de retirer le balisage général : tout ce qui suit est un
# appendice (étymologie, citations historiques en ancien français, notes de
# supplément), jamais un complément que le joueur a besoin de lire, et
# couper est nettement plus sûr qu'essayer de préserver sélectivement le
# contenu utile d'une section de supplément (qui mélangerait souvent
# elle-même sa propre parenthèse phonétique et ses propres citations).
_APPENDIX_BANNER = re.compile(
    r"<big>(?:ÉTYMOLOGIE|HISTORIQUE|SUPPLÉMENT AU DICTIONNAIRE|"
    r"REMARQUES?|SYNONYME|PROVERBES?)</big>"
)

_TOKEN = re.compile(r"[\w-]+")


def _mask_family(text: str, target: str) -> str:
    """Masque le mot cible et sa famille morphologique.

    Les entrées hyphénées (« avant-hier ») sont traitées comme un seul
    token pour que le mot composé cible soit reconnu d'un bloc ; chaque
    segment séparé par un tiret est aussi vérifié individuellement pour
    ne pas laisser passer un composé qui contiendrait la cible en partie
    (masquage volontairement large : mieux vaut masquer trop que pas assez).
    """
    folded = fold(target)
    prefix_length = max(5, len(folded) - 3)
    prefix = folded[:prefix_length]

    def matches(word: str) -> bool:
        return fold(word).startswith(prefix)

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        if matches(token) or any(matches(part) for part in token.split("-") if part):
            return "***"
        return token

    return _TOKEN.sub(replace, text)


def _finish_cleaning(text: str, target: str, max_chars: int) -> str:
    """Applique toutes les étapes de nettoyage à un texte déjà coupé au
    point d'entrée voulu (voir clean_definition). Isolée pour pouvoir être
    retentée sur plusieurs points de coupure candidats.
    """
    # Une balise retirée ne doit jamais souder deux mots ensemble (voir
    # _detag). Les espaces introduites — y compris en tête/en queue — sont
    # éliminées par le tassement d'espaces qui suit immédiatement.
    text = _detag(text)
    text = _WHITESPACE.sub(" ", text).strip()

    # La transcription phonétique épelle le mot : elle doit sauter. Les
    # entrées réelles enchaînent des combinaisons variées de structure avant
    # la prose : parenthèse phonétique, marqueur grammatical, jonction par
    # virgule (entrées à double genre : "(le mâle), s. f. (la femelle)"),
    # connecteur de variante ("ou", "au plur."), mot-vedette alternatif tout
    # en capitales avec sa propre parenthèse ("OGRESSE (o-grè-s')"), marqueur
    # de sens ("1°", "2."). N'importe laquelle de ces briques peut se trouver
    # en tête, dans n'importe quel ordre et répétée : on boucle jusqu'à
    # stabilité pour toutes les retirer, pas seulement la première rencontrée.
    previous = None
    while text != previous:
        previous = text
        text = _LEADING_PARENS.sub("", text)
        text = _GRAMMAR_MARKER.sub("", text)
        text = _LEADING_JUNCTION.sub("", text)
        text = _LEADING_CONNECTIVE.sub("", text)
        text = _LEADING_ALT_HEADWORD.sub("", text)
        text = _LEADING_SENSE.sub("", text)

    text = _SECOND_SENSE.split(text)[0]
    text = _CITATION.sub("", text)
    text = _mask_family(text, target)
    # Filet de sécurité indépendant : une parenthèse de forme phonétique qui
    # aurait survécu ailleurs dans le texte (ex. une bannière de supplément
    # au milieu de l'entrée) saute elle aussi, où qu'elle se trouve.
    text = _PHONETIC_PAREN.sub("", text)
    text = _WHITESPACE.sub(" ", text).strip()

    if len(text) > max_chars:
        cut = text[:max_chars].rsplit(" ", 1)[0]
        text = cut + "…"

    return text.strip()


def clean_definition(raw: str, target: str, max_chars: int = 220) -> str:
    """Transforme une entrée Littré brute en un indice lisible.

    Ordre imposé : le balisage part en premier pour que la parenthèse
    phonétique devienne détectable en tête de chaîne.
    """
    # Coupe avant la première bannière d'appendice (voir _APPENDIX_BANNER) —
    # étape ajoutée avant le retrait du balisage général, sans réordonner
    # les étapes existantes. Cas limite vérifié sur les 93 313 entrées de
    # l'index réel (une seule touchée, "ancêtre") : une entrée dont TOUTE la
    # définition utile ne vit que dans une section de supplément, sans rien
    # avant la première bannière. Couper là donnerait une définition vide,
    # ce qu'aucune bannière ne justifie de préférer à une définition non
    # vide. On retente donc, dans l'ordre, chaque point de coupure suivant
    # (bannière suivante, ...) jusqu'au texte complet non coupé — préserver
    # une définition non vide prime sur l'élimination de la bannière dans
    # ce cas limite seulement ; pour toutes les autres entrées, le contenu
    # avant la première bannière est déjà non vide et ce repli ne joue pas.
    cut_points = [match.start() for match in _APPENDIX_BANNER.finditer(raw)]
    candidates = [raw[:point] for point in cut_points]
    candidates.append(raw)

    for candidate in candidates:
        cleaned = _finish_cleaning(candidate, target, max_chars)
        if cleaned:
            return cleaned

    return ""


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
