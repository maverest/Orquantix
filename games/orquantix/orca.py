from __future__ import annotations

from games.orquantix import engine

# Bornes de rang, du plus lointain au plus proche. Un rang strictement
# supérieur au seuil donne l'humeur associée ; hors du top 1000, c'est « sick ».
MOOD_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (551, "vexed"),
    (176, "intrigued"),
    (31, "overexcited"),
    (1, "solar"),
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


def mood_for(rank: int | None, *, found: bool = False) -> str:
    """Humeur de l'orque pour un rang de voisin donné.

    Indexée sur le rang et non sur la barre de progression : la barre est
    presque plate jusqu'au rang 300, alors que l'orque doit réagir bien avant.
    """
    if found:
        return "found"
    if rank is None or rank > 1000:
        return "sick"
    for floor, mood in MOOD_THRESHOLDS:
        if rank >= floor:
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


def feedback(rank: int | None, *, found: bool = False) -> dict:
    """Tout ce dont le frontend a besoin pour afficher une ligne.

    La progression et l'humeur dérivent toutes deux du rang, seule mesure
    dont le joueur a besoin : le cosinus brut n'est plus affiché nulle part.
    """
    mood = mood_for(rank, found=found)
    return {
        "progress": engine.progress(rank, found=found),
        "rank": rank if (rank is not None and rank <= 1000) else None,
        "mood": mood,
        "emoji": emoji(mood),
        "beast": beast_label(mood),
        "label": proximity_label(mood),
        "rank_label": rank_label(rank, found=found),
        "found": found,
    }
