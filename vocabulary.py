import csv
from unidecode import unidecode


def normalize(word: str) -> str:
    """Lowercase + remove accents."""
    return unidecode(word.lower())


def build_norm_map(words: list[str]) -> dict[str, str]:
    """Map normalized form → original form. Last writer wins on collision."""
    return {normalize(w): w for w in words}


def _is_eligible_row(row: dict) -> bool:
    """Return True if this Lexique383 row passes the grammatical filter.

    Supports both the numbered column format used in tests (1_ortho, 3_lemme…)
    and the real Lexique383 format (ortho, lemme…).
    """
    ortho = row.get("ortho") or row.get("1_ortho", "")
    lemme = row.get("lemme") or row.get("3_lemme", "")
    cgram = row.get("cgram") or row.get("4_cgram", "")
    genre = row.get("genre") or row.get("5_genre", "")
    nombre = row.get("nombre") or row.get("6_nombre", "")

    # No spaces, hyphens or apostrophes
    if any(c in ortho for c in (" ", "-", "'")):
        return False

    # NOM singulier ou invariable (nombre vide = mot invariable ex: bordeaux)
    if cgram == "NOM" and nombre in ("s", ""):
        return True
    # ADJ masculin singulier ou invariable (ex: mauve, rose, turquoise)
    if cgram == "ADJ" and genre in ("m", "") and nombre in ("s", ""):
        return True
    if cgram == "VER" and ortho == lemme:  # infinitive: form equals lemma
        return True
    return False


def filter_eligible_words(
    tsv_path: str,
    model_vocab: set[str],
    min_freq: float = 5.0,
) -> tuple[list[str], dict[str, float]]:
    """
    Read Lexique383 TSV, apply grammatical + frequency filter, intersect with
    model vocabulary.

    Supports both real Lexique383 column names (ortho, lemme, cgram…) and
    the numbered test format (1_ortho, 3_lemme, 4_cgram…).

    Returns:
        vocab: eligible words sorted by frequency descending
        freq_by_word: {word: freqlemlivres}
    """
    freq_by_word: dict[str, float] = {}

    with open(tsv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            ortho = row.get("ortho") or row.get("1_ortho", "")
            if not _is_eligible_row(row):
                continue
            try:
                freq = float(row.get("freqlemlivres") or row.get("7_freqlemlivres") or 0)
            except ValueError:
                freq = 0.0
            if freq < min_freq:
                continue
            if ortho not in model_vocab:
                continue
            # Keep highest frequency if word appears multiple times
            if ortho not in freq_by_word or freq > freq_by_word[ortho]:
                freq_by_word[ortho] = freq

    vocab = sorted(freq_by_word, key=freq_by_word.__getitem__, reverse=True)
    return vocab, freq_by_word


def compute_difficulty_thresholds(
    vocab: list[str],
    freq_by_word: dict[str, float],
) -> list[float]:
    """
    Return 4 ascending frequency thresholds [q20, q40, q60, q80] that divide
    vocab into 5 equal-size groups (quintiles).
    """
    freqs = sorted(freq_by_word.get(w, 0.0) for w in vocab)
    n = len(freqs)
    if n == 0:
        return [0.0, 0.0, 0.0, 0.0]
    return [freqs[max(0, n * i // 5)] for i in (1, 2, 3, 4)]
