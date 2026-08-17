import hashlib
from datetime import date

from gensim.models import KeyedVectors

NEIGHBOURHOOD_SIZE = 1000
PROGRESS_EXPONENT = 3.4
FOUND_PROGRESS = 100.0
MAX_NEIGHBOUR_PROGRESS = 99.99


def get_neighbours(model, target: str, topn: int = NEIGHBOURHOOD_SIZE) -> list[tuple[str, float]]:
    """Les voisins les plus proches, du plus proche au plus lointain."""
    limit = min(topn, len(model.key_to_index) - 1)
    return model.most_similar(target, topn=limit)


def progress(rank: int | None, *, found: bool = False) -> float:
    """Rang du voisin → pourcentage de progression.

    Courbe volontairement très plate en bas : au rang 800 elle vaut 0,43 %,
    au rang 400 environ 18 %, et elle ne décolle vraiment que dans le top 100.
    C'est délibéré. Le top 1000 représente les 3,2 % de mots les plus proches
    sur 31 548 — y entrer n'est pas « chaud », et un voisin de rang 800
    n'apprend rien au joueur. Une échelle qui le montrerait à mi-hauteur
    mentirait, et ferait de surcroît doublon avec la colonne Rang, qui dit
    déjà qu'on est dans le top 1000.
    """
    if found:
        return FOUND_PROGRESS
    if rank is None or rank < 1 or rank > NEIGHBOURHOOD_SIZE:
        return 0.0
    ratio = (NEIGHBOURHOOD_SIZE + 1 - rank) / NEIGHBOURHOOD_SIZE
    return round(min(ratio**PROGRESS_EXPONENT * 100, MAX_NEIGHBOUR_PROGRESS), 2)


def get_daily_word(vocab: list[str], game_index: int = 0) -> str:
    """
    Deterministic word selection based on today's date and game_index.
    seed = "YYYY-MM-DD-N"
    """
    seed = f"{date.today().isoformat()}-{game_index}"
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return vocab[h % len(vocab)]


def get_difficulty(
    word: str,
    freq_by_word: dict[str, float],
    thresholds: list[float],
) -> int:
    """
    Return 1 (easy/frequent) to 5 (hard/rare).
    thresholds: 4 ascending values from compute_difficulty_thresholds().
    freq >= thresholds[3] → difficulty 1 (top quintile)
    freq <  thresholds[0] → difficulty 5 (bottom quintile)
    """
    freq = freq_by_word.get(word, 0.0)
    for i, t in enumerate(reversed(thresholds)):
        if freq >= t:
            return i + 1
    return 5


def get_score(model: KeyedVectors, word: str, target: str) -> float:
    """Cosine similarity × 100, rounded to 2 decimal places."""
    return round(float(model.similarity(word, target)) * 100, 2)


def rank_map(neighbours: list[tuple[str, float]]) -> dict[str, int]:
    """Rang de chaque voisin dans une liste déjà calculée (rank=1 = plus proche)."""
    return {word: rank + 1 for rank, (word, _) in enumerate(neighbours)}
