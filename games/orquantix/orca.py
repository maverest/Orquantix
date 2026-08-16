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
