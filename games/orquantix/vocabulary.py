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
