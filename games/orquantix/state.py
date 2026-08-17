from __future__ import annotations

import threading

from games.orquantix.vocabulary import Pools


class OrquantixState:
    """État d'Orquantix, isolé de la coquille.

    Vit côté serveur : c'est ce qui permet de quitter vers le menu et de
    retrouver sa partie en revenant.

    Le loader tourne sur un thread de fond pendant que les requêtes sont
    servies depuis d'autres. `update()` couvre les affectations simples,
    mais deux opérations sont des transactions à part entière et ne doivent
    jamais être reconstruites au niveau appelant par des affectations
    directes : enregistrer une réponse (`record_guess`) et démarrer une
    nouvelle manche (`start_new_round`), qui avance `game_index` et
    remplace mot/échelle/voisins/réponses comme un seul geste atomique.
    """

    def __init__(self) -> None:
        self.phase: str = "idle"  # idle | downloading | loading | ready | error
        self.progress: int = 0
        self.detail: str = ""
        self.model = None
        self.littre = None
        self.pools: Pools | None = None
        self.neighbours: list[tuple[str, float]] = []
        self.top1000: dict[str, int] = {}
        self.norm_to_model: dict[str, str] = {}
        self.difficulty_thresholds: list[float] = []
        self.mystery_word: str = ""
        self.difficulty: int = 0
        self.game_index: int = 0
        self.guesses: list[dict] = []
        self._lock = threading.Lock()

    def update(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                setattr(self, key, value)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "phase": self.phase,
                "progress": self.progress,
                "detail": self.detail,
            }

    def record_guess(self, round_index: int, entry: dict) -> bool:
        """Ajoute `entry` à `self.guesses`, mais seulement si `round_index`
        (capturé par l'appelant via `self.game_index` avant de calculer sa
        réponse) correspond toujours à la manche en cours.

        Si une nouvelle manche a démarré entre-temps, `game_index` a changé
        et l'ajout est silencieusement abandonné plutôt que de muter la
        liste de la manche suivante (la réponse a été calculée contre
        l'ancien mot mystère, elle n'a rien à faire là) ou un objet déjà
        remplacé par `start_new_round` que plus rien ne référence. Renvoie
        si l'ajout a eu lieu.
        """
        with self._lock:
            if round_index != self.game_index:
                return False
            self.guesses.append(entry)
            return True

    def start_new_round(
        self,
        *,
        mystery_word: str,
        neighbours: list[tuple[str, float]],
        top1000: dict[str, int],
        difficulty: int,
    ) -> int:
        """Démarre une nouvelle manche comme une seule transition atomique.

        `game_index` avance et les champs de la manche (mot mystère,
        échelle, voisins, top1000, difficulté, réponses) changent tous sous
        le même verrou : aucun appelant ne peut observer `game_index` déjà
        avancé pendant que le reste appartient encore à l'ancienne manche,
        ni l'inverse. Renvoie le nouveau `game_index`.
        """
        with self._lock:
            self.game_index += 1
            self.mystery_word = mystery_word
            self.neighbours = neighbours
            self.top1000 = top1000
            self.difficulty = difficulty
            self.guesses = []
            return self.game_index
