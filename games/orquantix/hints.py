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
