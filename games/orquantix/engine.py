import hashlib
from dataclasses import dataclass
from datetime import date

import numpy as np
from gensim.models import KeyedVectors

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


ORCA_EMOJIS = {
    "sick": "🤢",
    "vexed": "😤",
    "intrigued": "🤨",
    "overexcited": "🤯",
    "solar": "☀️",
    "found": "☀️",
}


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


def get_top1000(model: KeyedVectors, target: str) -> dict[str, int]:
    """
    Compute up to 1000 nearest neighbors of target.
    Returns {word: rank} where rank=1 is the closest neighbor.
    Target word itself is excluded.
    """
    topn = min(1000, len(model.key_to_index) - 1)
    neighbors = model.most_similar(target, topn=topn)
    return {word: rank + 1 for rank, (word, _) in enumerate(neighbors)}


def get_orca_mood(rank: int | None, found: bool = False) -> str:
    if found:
        return "found"
    if rank is None or rank > 1000:
        return "sick"
    if rank >= 551:
        return "vexed"
    if rank >= 176:
        return "intrigued"
    if rank >= 31:
        return "overexcited"
    return "solar"


def get_proximity_label(rank: int | None, found: bool = False) -> str:
    if found:
        return "Trouvé"
    if rank is None or rank > 1000:
        return "Très loin"
    if rank >= 551:
        return "L'orque est vexé"
    if rank >= 176:
        return "L'orque s'intrigue"
    if rank >= 31:
        return "L'orque s'emballe"
    return "L'orque devient solaire"


def get_orca_beast_label(rank: int | None, found: bool = False) -> str:
    mood = get_orca_mood(rank, found)
    labels = {
        "sick": "Malade",
        "vexed": "Vexé",
        "intrigued": "Intrigué",
        "overexcited": "Surexcité",
        "solar": "Solaire",
        "found": "Solaire",
    }
    return labels[mood]


def get_rank_label(rank: int | None, found: bool = False) -> str:
    if found:
        return "Mot mystère trouvé"
    if rank is None or rank > 1000:
        return "Hors top 1000"
    return f"Voisin #{rank}"


def get_better_hint_word(
    top1000: dict[str, int],
    best_rank: int | None,
    guessed_words: set[str] | None = None,
) -> str | None:
    guessed_words = guessed_words or set()
    candidates = sorted(top1000.items(), key=lambda item: item[1])
    if not candidates:
        return None

    if best_rank is None or best_rank > 1000:
        target_rank = min(850, candidates[-1][1])
    elif best_rank <= 1:
        return None
    else:
        step = max(1, best_rank // 5)
        target_rank = max(1, best_rank - step)

    better_candidates = [
        (word, rank)
        for word, rank in candidates
        if rank <= target_rank and word not in guessed_words
    ]
    if not better_candidates and best_rank not in (None, 0):
        better_candidates = [
            (word, rank)
            for word, rank in candidates
            if rank < best_rank and word not in guessed_words
        ]
    if not better_candidates:
        return None

    better_candidates.sort(key=lambda item: (abs(item[1] - target_rank), item[1]))
    return better_candidates[0][0]


def get_strong_hint_word(
    top1000: dict[str, int],
    guessed_words: set[str] | None = None,
) -> str | None:
    guessed_words = guessed_words or set()
    candidates = sorted(top1000.items(), key=lambda item: item[1])
    if not candidates:
        return None

    for max_rank in (10, 25, 50, 100):
        for word, rank in candidates:
            if rank <= max_rank and word not in guessed_words:
                return word

    for word, _rank in candidates:
        if word not in guessed_words:
            return word
    return None
