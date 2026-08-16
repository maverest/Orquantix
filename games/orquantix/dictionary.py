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
_LEADING_PARENS = re.compile(r"^\s*\([^)]*\)\s*")
_GRAMMAR_MARKER = re.compile(
    r"^\s*(s\.\s*[mf]\.(\s*et\s*f\.)?|adj\.|v\.\s*[an]\.|adv\.)\s*",
    re.IGNORECASE,
)
_SECOND_SENSE = re.compile(r"\s*2°")
_FIRST_SENSE_MARKER = re.compile(r"^\s*1°\s*")
_CITATION = re.compile(r",?\s*[A-ZÀ-Ý]{4,}\.[^.]*\.")
_WHITESPACE = re.compile(r"\s+")


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


def clean_definition(raw: str, target: str, max_chars: int = 220) -> str:
    """Transforme une entrée Littré brute en un indice lisible.

    Ordre imposé : le balisage part en premier pour que la parenthèse
    phonétique devienne détectable en tête de chaîne.
    """
    text = _TAG.sub("", raw)
    text = _WHITESPACE.sub(" ", text).strip()

    # La transcription phonétique épelle le mot : elle doit sauter. Certaines
    # entrées (ex. "chien") enchaînent plusieurs groupes parenthèse + marqueur
    # grammatical ("(chiin) s. m. (le mâle), s. f. (la femelle)") : on boucle
    # jusqu'à stabilité pour tous les retirer, pas seulement le premier.
    previous = None
    while text != previous:
        previous = text
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
