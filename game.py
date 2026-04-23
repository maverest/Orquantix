import hashlib
from datetime import date

from gensim.models import KeyedVectors


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


def get_progress_percent(rank: int | None, found: bool = False) -> float:
    if found:
        return 100.0
    if rank is None or rank < 1 or rank > 1000:
        return 0.0
    base_progress = (1001 - rank) / 1000
    progress = (base_progress ** 3.4) * 100
    return round(min(progress, 99.99), 2)


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


def get_proximity_feedback(rank: int | None, found: bool = False) -> dict[str, str | float | bool | None]:
    mood = get_orca_mood(rank, found)
    return {
        "progress": get_progress_percent(rank, found),
        "rank": rank,
        "mood": mood,
        "beast": get_orca_beast_label(rank, found),
        "label": get_proximity_label(rank, found),
        "emoji": ORCA_EMOJIS[mood],
        "rank_label": get_rank_label(rank, found),
        "found": found,
    }


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
